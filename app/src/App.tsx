import { useEffect, useState } from 'react';
import { TakeoffN1Calculator } from './TakeoffN1Calculator';
import { TrimCalculator } from './TrimCalculator';
import { Outlet, Link } from 'react-router-dom'
import useWebSocket, { ReadyState } from 'react-use-websocket';

type WebsocketData = {
  message: string
  success: boolean
  max_n1: number
}

export const App = () => {

  return (
    <div className="flex">
      <Outlet />
      <div className="fixed flex bottom-0 right-0 h-[80px] w-screen justify-center items-center">
        <div className="fixed w-[90%] h-max bg-black m-4 py-2 rounded-xl text-white flex justify-evenly items-center">
          <Link className="hover:text-blue-700 cursor-pointer" to="/perf">PERF</Link>
          <Link className="hover:text-blue-700 cursor-pointer" to="/pax">PAX</Link>
        </div>
      </div>
    </div>
  )

}

export const PerfPage = () => {
  
  const [derate, setDerate] = useState("TO");
  const [maxN1, setmaxN1] = useState(104.0)
  const WS_URL = "ws://localhost:8000/x-plane/max-n1-ws"
  const {sendJsonMessage, lastJsonMessage, readyState} = useWebSocket(
    WS_URL,
    {
      share: false,
      shouldReconnect: () => true
    }
  )
  useEffect(() => {
    if(readyState === ReadyState.OPEN) {
      sendJsonMessage({
        request: "sub_max_n1"
      })
    }
  }, [readyState, sendJsonMessage])

  useEffect(() => {
    if(!lastJsonMessage) return

    const data: WebsocketData = lastJsonMessage as WebsocketData
    console.log(lastJsonMessage)
    if(!data.success && data.message != "Success") return
    setmaxN1(data.max_n1)
    sendJsonMessage({
      request: "ping",
    })
  }, [lastJsonMessage, sendJsonMessage])



  return (
    <div className="dark bg-[#333333] h-screen w-screen">
      <div className="flex justify-evenly items-center text-5xl gap-2">
        <TakeoffN1Calculator derate={derate} setDerate={setDerate} />
        <TrimCalculator derate={derate} />
      </div>
      <h1 className="text-white text-xl">Max N1: {maxN1}</h1>
    </div>

  )
}

export const PaxPage = () => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_pax, _setPax] = useState(0);

  // useEffect(() => {
  //   const interval = setInterval(() => {
  //     setPax(prevPax => prevPax+1)
  //   }, (1000*60)/12)

  //   return () => clearInterval(interval)
  // }, [])


  return (
    <div className="dark bg-[rgb(51,51,51)] h-screen w-screen text-white flex justify-evenly items-center flex-col">
      <div className='flex flex-col items-center'>
        <h1 className='text-2xl'>737 KQA Safety Announcement</h1>
        <audio controls>
          <source src="737kqasafety.mp3" type="audio/mp3"></source>
        </audio>
      </div>
      <div className='flex flex-col items-center'>
        <h1 className='text-2xl'>787 KQA Safety Announcement</h1>
        <audio controls>
          <source src="787kqasafety.mp3" type="audio/mp3"></source>
        </audio>
      </div>
    </div>
  )
}