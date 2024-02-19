import React, { useState, useEffect, StrictMode, useRef, useCallback } from 'react'
import { LineChartStatic } from "../RecordedMotions/RecordedMotions.tsx"
import { PacketHeader, copy_packet } from "../types.ts"
import "./motion_review.css"

//src https://gist.github.com/mubaidr/1a6596eae71215fdd578be2a406e8a15
export function applyMedianFilter(
    data: Uint8ClampedArray,
    width: number,
    height: number,
    windowSize = 3
  ): Uint8ClampedArray {
    const channels = data.length / (width * height)
    const filterWindow: number[][] = []
    const limit = (windowSize - 1) / 2
  
    for (let i = limit * -1; i < limit + 1; i += 1) {
      for (let j = limit * -1; j < limit + 1; j += 1) {
        filterWindow.push([i, j])
      }
    }
  
    for (let col = limit; col < width - limit; col += 1) {
      for (let row = limit; row < height - limit; row += 1) {
        const index = (row * width + col) * channels
        const arr: number[] = []
  
        for (let z = 0; z < filterWindow.length; z += 1) {
          const i = ((row + filterWindow[z][0]) * width + (col + filterWindow[z][1])) * channels
          const average = Math.sqrt((data[i] ** 2 + data[i + 1] ** 2 + data[i + 2] ** 2) / 3)
  
          arr.push(average)
        }
  
        const sorted = arr.sort((a, b) => a - b)
        const medianValue = sorted[Math.floor(sorted.length / 2)]
  
        data[index + 0] = medianValue
        data[index + 1] = medianValue
        data[index + 2] = medianValue
  
        if (channels === 4) data[index + 3] = 255
      }
    }
  
    return data
  }

export function MotionReview({ }) {
    let [motions, set_motions] = useState<Object>({})

    useEffect(() => {
        const process_motions = async (data) => {
            let motions_dict = {}

            for (const element of data) {
                if (!motions_dict[element.label]) motions_dict[element.label] = []

                try {
                    let response = await fetch(`/recorded_motions/get_motion?id=${element.id}`)
                    element.packets = (await response.json()).map(val => { return JSON.parse(val) })
                }
                catch (error) {
                    console.error(`ERROR FETCHING MOTION ${element.id}`, error)
                }
                motions_dict[element.label].push(element)

            };
            return motions_dict
        }

        const fetch_motions_head = async () => {
            try {
                const response = await fetch(`/recorded_motions?label=${"any"}`);
                const data = await response.json();

                return data

            } catch (error) {
                console.error("Error fetching data:", error);
                return null
            }
        };
        const get_motion_data = async () => {

            let data = await fetch_motions_head()
            if (!data) { return }
            let motions_dict = await process_motions(data)
            set_motions(motions_dict);
        }
        get_motion_data()
    }, [])
    const [BTW, set_LPD] = useState(false);
    const [FFT, set_FFT] = useState(false);
    const [MED, set_MED] = useState(false);
    /*TODO*/


    return <div>
        <div style={{ display: "flex", width: "100%", height: "10%", backgroundColor: "var(--color-black)", color: "white", padding: "2rem" }}>
            <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginRight: "1rem"
            }}>
                MOTION REVIEW
            </div>
            <div style={{ marginRight: "1rem" }} className={'button ' + (MED ? "motion_review_button_on" : "")} onClick={() => { set_MED((old) => !old) }}>
                MEDIAN FILTER
            </div>
            <div style={{ marginRight: "1rem" }} className={'button ' + (BTW ? "motion_review_button_on" : "")} onClick={() => { set_LPD((old) => !old) }}>
                BUTTERWORTH 
            </div>
            <div style={{ marginRight: "1rem" }} className={'button ' + (FFT ? "motion_review_button_on" : "")} onClick={() => { set_FFT((old) => !old) }}>
                FFT
            </div>

        </div>
        {Object.keys(motions).map((motion_type, index) => {
            return <div key={index} >

                {motions[motion_type].map((motion, index) => {
                    let { acc_readings_linear, gyro_readings_linear } = packet_as_linear_array(motion.packets)
                    return <div key={index} style={{ marginBottom: "3rem", display: "flex", width: "50%", height: "40%", color: "white" }}>
                        <div style={{ position: 'relative', backgroundColor: "var(--color-black)" }}>
                            <span style={{ position: "absolute", top: "5px", left: "6%" }}>
                                Accelerometer
                            </span>
                            <div style={{ display: "flex", flexDirection: "row", overflow: "scroll", width: "40vw" }}>
                                {motion.shapes_acce.map(
                                    (shape,index) => {
                                        return <LineChartStatic key={index} shapes={[]}
                                            x={acc_readings_linear[0].slice(shape.start, shape.end)}
                                            y={acc_readings_linear[1].slice(shape.start, shape.end)}
                                            z={acc_readings_linear[2].slice(shape.start, shape.end)}
                                            width={500} height={200} on_click={null} />
                                    })}
                            </div>
                        </div>

                        <div style={{ position: 'relative', backgroundColor: "var(--color-black)" }}>
                            <span style={{ position: "absolute", top: "5px", left: "6%" }}>
                                Gyroscope
                            </span>
                            <div style={{ display: "flex", flexDirection: "row", overflow: "scroll", width: "40vw" }}>
                                {motion.shapes_acce.map(
                                    (shape,index) => {
                                        return <LineChartStatic key={index}  shapes={[]}
                                            x={gyro_readings_linear[0].slice(shape.start, shape.end)}
                                            y={gyro_readings_linear[1].slice(shape.start, shape.end)}
                                            z={gyro_readings_linear[2].slice(shape.start, shape.end)}
                                            width={500} height={200} on_click={null} />
                                    })}
                            </div>
                        </div>
                        </div>
                        

                })}
            </div>
        })}
    </div>
}