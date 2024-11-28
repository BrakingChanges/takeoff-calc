import pandas as pd
from enum import Enum
from scipy.interpolate import RegularGridInterpolator
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket
import socket
from fastapi.middleware.cors import CORSMiddleware
import websocket
from x_plane_udp import XPlaneUdp, XPlaneIpNotFound

app = FastAPI(title="737-800W(B738) Performance Data and Manipulation API")


origins = [
    "http://localhost:4173",
    "http://localhost:5173",
    "http://localhost",
    f"http://{socket.gethostbyname(socket.gethostname())}:5173",
    f"http://{socket.gethostbyname(socket.gethostname())}:4173"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


derates = {
    'TO': '26K',
    'TO-1': '24K',
    'TO-2': '22K'
}


class TakeoffDerates(str, Enum):
    to = 'TO'
    to1 = 'TO-1'
    to2 = 'TO-2'


class TakeoffCalculationRequest(BaseModel):
    derate: TakeoffDerates
    assumed_temp: int
    press_altitude: int
    oat: int
    bleeds: bool

class TrimCalculationRequest(BaseModel):
    weight: float
    cg: float
    derate: TakeoffDerates

class DerateN1Request(BaseModel):
    derate_N1: float


pressure_factor = {
    'hpa': 1/3386/100,
    'in': 1
}


def create_interpolator(df: pd.DataFrame):
    """ creats an interpolation function to find N1 from an assumed dataset"""
    unique_temps = df['Assumed Temperature (C)'].unique()
    unique_alts = df['Airport Pressure Altitude (ft)'].unique()

    # Create a 2D grid of the N1 values
    n1_matrix = df.pivot(
        index='Airport Pressure Altitude (ft)',
        columns='Assumed Temperature (C)',
        values='N1 (%)'
    ).values

    # Create the interpolation function

    return RegularGridInterpolator((unique_alts, unique_temps), n1_matrix)

def create_interpolator_stab_trim(df: pd.DataFrame):
    unique_weights = df['Weight(kg)'].unique()
    unique_cg_settings = df['CG(%MAC)'].unique()

    trim_matrix = df.pivot(
        index='Weight(kg)',
        columns='CG(%MAC)',
        values='Trim'
    ).values

    return RegularGridInterpolator((unique_weights, unique_cg_settings), trim_matrix)


def create_interpolator_n1_reduction(df: pd.DataFrame):
    unique_delta_assumed_temp = df['Assumed Temp Minus OAT'].unique()
    unique_oat = df['OAT'].unique()

    n1_red_matrix = df.pivot(
        index='Assumed Temp Minus OAT',
        columns='OAT',
        values='N1(%) Reduction'
    ).values

    return RegularGridInterpolator((unique_delta_assumed_temp, unique_oat), n1_red_matrix)


# Function to find N1 based on pressure altitude and assumed temperature


def find_n1(pressure_altitude: float, assumed_temp: int, interp_func: RegularGridInterpolator):
    """Alias function to find N1 using interpolation function"""
    return interp_func((pressure_altitude, assumed_temp))

def find_trim(weight: float, cg: float, interp_func: RegularGridInterpolator):
    return interp_func((weight, cg))

def find_n1_reduction(assumed_temp_minus_oat: int, oat: int, interp_func: RegularGridInterpolator):
    return interp_func((assumed_temp_minus_oat, oat))

@app.post('/takeoff/derate')
def get_n1(takeoff_request: TakeoffCalculationRequest):
    derate_database = pd.read_csv(f'data-{derates[takeoff_request.derate]}.csv')
    
        
    
    derate_database.columns = ['Assumed Temperature (C)', 'Airport Pressure Altitude (ft)',
                               'N1 (%)', 'Minimum Assumed Temperature (C)']
    n1 = find_n1(takeoff_request.press_altitude,
                 takeoff_request.assumed_temp, create_interpolator(derate_database))
    
    n1_red = 0
    n1_red_database = pd.read_csv(f'data-reduction-{derates[takeoff_request.derate]}.csv')
    n1_red_database.columns = ['Assumed Temp Minus OAT', 'OAT', 'N1(%) Reduction']
    n1_red = float(find_n1_reduction(takeoff_request.assumed_temp - takeoff_request.oat, takeoff_request.oat, create_interpolator_n1_reduction(n1_red_database)))

    return {
        "success": True,
        "message": "Success",
        "n1": round(float(n1) - n1_red, 1) if takeoff_request.bleeds else round(float(n1) - n1_red, 1) + 1
    }

@app.post('/takeoff/trim')
def get_trim(trim_request: TrimCalculationRequest):
    if trim_request.derate not in [TakeoffDerates.to, TakeoffDerates.to1]:
        return  {
            "success": False,
            "message": "Unsupported derate"
        }
    stab_trim_database = pd.read_csv(f"Stab Trim {derates[trim_request.derate]} F1+5.csv")
    stab_trim_database.columns = ['Weight(kg)', 'CG(%MAC)', 'Trim']

    trim = find_trim(trim_request.weight, trim_request.cg, create_interpolator_stab_trim(stab_trim_database))

    return {
        "success": True,
        "message": "Success",
        "trim": round(float(trim) * 4)/4
    }

@app.post('/x-plane/set-derate')
def set_derate(derate_request: DerateN1Request):
    try:
        udp_conn = XPlaneUdp()
        x_plane_beacon = udp_conn.find_ip()
        print(
            f"{x_plane_beacon.ip}:{x_plane_beacon.port}"
        )
        udp_conn.write_data_ref("sim/cockpit2/engine/actuators/N1_target_bug", derate_request.derate_N1)

        return {
            "success": True,
            "message": "Success"
        }
    except XPlaneIpNotFound:
        return {
            "success": False,
            "message": "No X-Plane Instance Found"
        }


@app.get('/x-plane/get-weight')
def get_weight():
    try:
        udp_conn = XPlaneUdp()
        x_plane_beacon = udp_conn.find_ip()
        print(
            f"{x_plane_beacon.ip}:{x_plane_beacon.port}"
        )
        udp_conn.add_data_ref("sim/flightmodel/weight/m_total")
        return {
            "success": True,
            "message": "Success",
            "weight": float(udp_conn.get_values()["sim/flightmodel/weight/m_total"])
        }
    except XPlaneIpNotFound:
        return {
            "success": False,
            "message": "No X-Plane Instance Found"
        }

# LEMAC: 793 in
@app.get('/x-plane/get-cg')
def get_cg():
    try:
        udp_conn = XPlaneUdp()
        udp_conn.find_ip()
        udp_conn.add_data_ref("sim/cockpit2/gauges/indicators/CG_indicator")
        cg =  float(udp_conn.get_values()["sim/cockpit2/gauges/indicators/CG_indicator"])
        udp_conn.add_data_ref("sim/cockpit2/gauges/indicators/CG_indicator", freq=0)

        return {
            "success": True,
            "message": "Success",
            "cg_mac": cg * 100,
            "cg_inches": 793 * (cg + 1)
        }
    except XPlaneIpNotFound:
        return {
            "success": False,
            "message": "No X-Plane Instance Found"
        }

@app.get("/x-plane/get-altitude")
def get_altitude():
    try:
        udp_conn = XPlaneUdp()
        udp_conn.find_ip()
        udp_conn.add_data_ref("sim/flightmodel2/position/pressure_altitude")
        return {
            "success": True,
            "message": "Success",
            "press_alt": float(udp_conn.get_values()["sim/flightmodel2/position/pressure_altitude"])
        }
    except XPlaneIpNotFound:
        return {
            "success": False,
            "message": "No X-Plane Instance Found"
        }


def get_press_alt(udp_conn: XPlaneUdp) -> float:
    udp_conn.add_data_ref("sim/weather/barometer_current_inhg")
    stat_press_inhg = float(udp_conn.get_values()["sim/weather/barometer_current_inhg"])
    stat_press_hpa = stat_press_inhg * 33.8639
    pressure_altitude = 145366.45 * (1 - (stat_press_hpa/1013.25)**0.190284)

    return pressure_altitude



# sim/weather/barometer_current_inhg
@app.get("/x-plane/get-press-alt")
def get_press_altitude():
    try:
        udp_conn = XPlaneUdp()
        udp_conn.find_ip()
        pressure_altitude = get_press_alt(udp_conn)


        return {
            "success": True,
            "message": "Success",
            "press_alt": pressure_altitude
        }
    except XPlaneIpNotFound:
        return {
            "success": False,
            "message": "No X-Plane Instance Found"
        }

def create_interpolator_n1_max(df: pd.DataFrame):
    unique_tat = df['TAT(C)'].unique()
    unique_pressure_altitude = df['Pressure Altitude(ft)'].unique()

    n1_matrix = df.pivot(
        index='TAT(C)',
        columns='Pressure Altitude(ft)',
        values='N1(%)'
    ).values

    return RegularGridInterpolator((unique_tat, unique_pressure_altitude), n1_matrix)

def find_max_n1(tat: float, press_alt: float, interp_func: RegularGridInterpolator) -> float:
    return float(interp_func((tat, press_alt)))

@app.websocket("/x-plane/max-n1-ws")
async def max_n1_ws(websocket: WebSocket):
    await websocket.accept()
    n1_subscription_status = False
    max_n1 = pd.read_csv("Max Climb N1%.csv")
    max_n1.columns = ['TAT(C)', 'Pressure Altitude(ft)', 'N1(%)']
    while True:
        
        if n1_subscription_status:
            try:
                udp_conn = XPlaneUdp()
                udp_conn.find_ip()
                press_alt = get_press_alt(udp_conn)
                udp_conn.add_data_ref("sim/cockpit2/temperature/outside_air_temp_deg")
                temp = float(udp_conn.get_values()["sim/cockpit2/temperature/outside_air_temp_deg"])

                press_alt = min(press_alt, 41000)
                
                press_alt = max(press_alt, 0)

                if temp < -40:
                    temp = -40
                
                temp = min(temp,0)
                
                max_n1_perc = find_max_n1(temp, press_alt, create_interpolator_n1_max(max_n1))

                await websocket.send_json({
                    "success": True,
                    "message": "Success",
                    "max_n1": max_n1_perc
                })
                print("Sent")
            except XPlaneIpNotFound:
                await websocket.send_json({
                    "success": "false",
                    "message": "No X-Plane Instance Found"
                })
        
        data = await websocket.receive_json()

        if data["request"] == "sub_max_n1":
            n1_subscription_status = True
        if data["request"] == "ping":
            await websocket.send({
                "success": True,
                "message": "pong",
            })    





