import { Input, Button, Switch } from "@nextui-org/react";
import { useState } from "react";

export const TrimCalculator = ({derate}: {derate: string}) => {
  const [acftWeight, setAcftWeight] = useState(0);
  const [acftCG, setAcftCG] = useState(0);
  const [trim, setTrim] = useState<number>();
  const [manualInputs, setManualInputs] = useState(false);

  const getTrim = async (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.preventDefault()

    const result = await fetch('http://localhost:8000/takeoff/trim', {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify({
        weight: acftWeight,
        cg: acftCG,
        derate: derate
      })
    })

    const data = await result.json()

    if(data.message !== 'Success') return
    const trim: number = data.trim
    setTrim(trim)
  }


  const getWeightAndCG = async (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.preventDefault()
    
    const weightResult = await fetch('http://localhost:8000/x-plane/get-weight')
    const cgResult = await fetch('http://localhost:8000/x-plane/get-cg')
    const weightData = await weightResult.json()
    const cgData = await cgResult.json()
    const weight: number = weightData.weight
    const cg: number = cgData.cg_mac
    setAcftWeight(weight)
    setAcftCG(cg)
  }


  return (
    <form className="flex flex-col gap-2 ">
      <h1 className="text-white">Trim Setting Calculator</h1>
      <Input
        disabled={!manualInputs}
        label="CG setting(%MAC)"
        value={acftCG.toString()}
        onChange={(e) => setAcftCG(Number(e.target.value))}
        type="number"
      ></Input>
      <Input
        disabled={!manualInputs}
        label="Aircraft Weight(kg)"
        value={acftWeight.toString()}
        onChange={(e) => setAcftWeight(Number(e.target.value))}
      ></Input>
      <Button color="primary" onClick={getTrim}>
        Calculate Trim
      </Button>
      <div className="flex justify-between">
        <Switch isSelected={manualInputs} onValueChange={setManualInputs}>
          Manual Selection
        </Switch>
        <Button onClick={getWeightAndCG} type="submit">
          Get CG & Weight From X-Plane
        </Button>
      </div>
      <strong className="text-white text-small">
        Please note that you need to have a running instance of X-Plane for
        automatic fetching to work
      </strong>

      {trim && (
        <>
          <p className="text-white text-large">Trim Setting: {trim} units</p>
        </>
      )}
    </form>
  );
};
