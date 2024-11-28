import { Input, Select, SelectItem, Button } from "@nextui-org/react";
import { FormEvent, useEffect, useState } from "react";

type PressureUnit = "inHG" | "hPa";

function isPressureUnit(str: string): str is PressureUnit {
  return str === "inHG" || str === "hPA";
}

// function isValidPressure(press: number): boolean {
//   if (press.toString().length !== 4 && press.toString().length !== 5)
//     return false;
//   if (press.toString().length === 5 && press.toString()[2] === ".") return true;
//   return true;
// }

// function isInHGPressure(press: number): boolean {
//   if (press.toString().length === 5 && press.toString()[2] === ".") return true;
//   return false;
// }

// function isHPaPressure(press: number): boolean {
//   if (press.toString().length === 4) return true;
//   return false;
// }

export const TakeoffN1Calculator = ({derate, setDerate}: {
  derate: string,
  setDerate: React.Dispatch<React.SetStateAction<string>>
}) => {
  const [aptElevation, setAptElevation] = useState(0);
  const [assumedTemp, setAssumedTemp] = useState(0);
  const [oat, setOat] = useState(0)
  const [bleeds, setBleeds] = useState("On")
  const [pressureUnit, setPressureUnit] = useState<PressureUnit>("inHG");

  const [pressureString, setPressureString] = useState("29.92");
  const [pressureStringValid, setPressureStringValid] = useState(true);

  const [n1, setN1] = useState<number>();
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    if (pressureString.length !== 5 && pressureString.length !== 4) {
      setPressureStringValid(false);
      return;
    }

    if (
      pressureUnit === "inHG" &&
      pressureString.length === 5 &&
      pressureString[2] === "." &&
      !isNaN(Number(pressureString))
    ) {
      setPressureStringValid(true);
      return;
    }

    if (
      pressureUnit === "hPa" &&
      pressureString.length !== 4 &&
      !isNaN(Number(pressureString))
    ) {
      setPressureStringValid(true);
      return;
    }

    setPressureStringValid(false);
  }, [pressureString, pressureUnit]);

  const submitTakeoff = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const reqBody = JSON.stringify({
      derate: derate,
      assumed_temp: assumedTemp,
      press_altitude: aptElevation,
      oat: oat,
      bleeds: bleeds === 'On' ? true : false
    });

    const result = await fetch("http://localhost:8000/takeoff/derate", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: reqBody,
    });
    const data = await result.json();
    const n1 = data.n1;
    setN1(n1);
  };

  const setXPN1 = async (
    e: React.MouseEvent<HTMLButtonElement, MouseEvent>
  ) => {
    e.preventDefault();
    const result = await fetch("http://localhost:8000/x-plane/set-derate", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        derate_N1: n1,
      }),
    });

    const data = await result.json();
    const message: string = data.message;
    setStatusMessage(message);

    setTimeout(() => {
      setStatusMessage("");
    }, 1000);
  };

  function onChangePressUnit(e: React.ChangeEvent<HTMLSelectElement>) {
    if (!isPressureUnit(e.target.value)) return;
	console.log("set")
    setPressureUnit(e.target.value);
  }

  return (
    <form onSubmit={submitTakeoff} className="flex flex-col gap-2">
      <h1 className="text-white">Takeoff N1 Calculator</h1>
      <Input
        label="Enter airport elevation(ft)"
        required
        type="number"
        value={aptElevation.toString()}
        onChange={(e) => setAptElevation(Number(e.target.value))}
      ></Input>
      <div className="flex gap-2">
        <Select
          required
          defaultSelectedKeys={[pressureUnit]}
          isRequired
          onChange={onChangePressUnit}
          aria-label="Pressure unit"
          variant="underlined"
        >
          <SelectItem key="inHG">inHG</SelectItem>
          <SelectItem key="hPa">hPa</SelectItem>
        </Select>
        <Input
          value={pressureString}
          onChange={(e) => setPressureString(e.target.value)}
          isInvalid={!pressureStringValid}
          errorMessage={"Inavlid pressure setting."}
        ></Input>
      </div>
      <Input
        label="Enter assumed temperature(C)"
        required
        type="number"
        value={assumedTemp.toString()}
        onChange={(e) => setAssumedTemp(Number(e.target.value))}
      ></Input>
      <Input label="Enter OAT(C)" required type="number" value={oat.toString()} onChange={e => setOat(Number(e.target.value))}>
      </Input>
      <Select
        label="Derate"
        required
        value={derate}
        onChange={(e) => setDerate(e.target.value)}
      >
        <SelectItem key="TO">TO</SelectItem>
        <SelectItem key="TO-1">TO-1</SelectItem>
        <SelectItem key="TO-2">TO-2</SelectItem>
      </Select>
      <Select label="Bleeds" required value={bleeds} onChange={e => setBleeds(e.target.value)}>
        <SelectItem key="On">On</SelectItem>
        <SelectItem key="Off">Off</SelectItem>
      </Select>
      <Button type="submit" color="primary">
        Submit
      </Button>
      {n1 && (
        <div className="m-5 flex justify-center items-center flex-col gap-2">
          <h1 className="text-white">N1: {n1}%</h1>
          <Button onClick={setXPN1}>Set N1</Button>
          <h1 className="text-white text-small">{statusMessage}</h1>
        </div>
      )}
    </form>
  );
};
