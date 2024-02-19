import React, { useState, useEffect, StrictMode, useRef, useCallback } from "react"
import { socket } from "../socket.ts"
import Plot from 'react-plotly.js';
import arrow_svg from "../svgs/arrow.svg";
import save_svg from "../svgs/save.svg";
import done_svg from "../svgs/done.svg";
import x_svg from "../svgs/x.svg";

import { PacketHeader, Packet, copy_packet, Motion } from "../types.ts"

export function LineChartStatic({ x, y, z, width, height, on_click = null, shapes = [] }: {
    x: number[], y: number[], z: number[], width: number, height: number, on_click: null | CallableFunction, shapes: any[]
}) {
    const colors = ['#f3cec9', '#a262a9', '#182844'];
    const colors_name = ['y', 'z', 'x'];

    function click_handle(data) {
        console.log("CLICK ")
        if (on_click) { on_click(data) }
    }

    return <span style={{ display: "flex", flexDirection: "row" }}>
        <span style={{ display: "flex", flexDirection: "column", width: `${width * .05}px`, height: `${height}px` }}>
            {

                colors.map((color, index) => {
                    return <div style={{
                        width: "100%",
                        height: "100%",
                        backgroundColor: `${color}`,
                        color: "#0E0F12",
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                    }}
                        key={index}
                    >
                        {colors_name[index]}
                    </div>
                })
            }

        </span>
        <Plot onClick={click_handle} data={[
            {
                y: y,
                type: 'scatter',
                mode: 'lines',
                name: 'y',
                line: { 'width': .9 },

            },
            {
                y: z,
                type: 'scatter',
                mode: 'lines',
                name: 'z',
                line: { 'width': .9 },

            },
            {
                y: x,
                type: 'scatter',
                mode: 'lines',
                name: 'x',
                line: { 'width': .9 },

            },
        ]} x={x}
            layout={{
                colorway: ['#f3cec9', '#a262a9', '#182844'],
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                selectdirection: "h",
                width: width * .95,
                height: height,
                shapes: shapes,
                font: {

                    color: "#F7F6F7"
                },
                xaxis: {
                    range: [0, x.length],
                    autorange: false,
                    showticklabels: false,
                    zeroline: false,
                    showgrid: false,
                    fixedrange: true

                },
                yaxis: {
                    range: [-32767, 32767],
                    autorange: false,
                    showticklabels: false,
                    zeroline: false,
                    showgrid: false,
                    fixedrange: true
                },
                margin: {
                    t: 20,
                    l: 20,
                    r: 20,
                    b: 20,
                },
                showlegend: false

            }}
            config={{
                displayModeBar: false

            }}
        />

    </span>
};

export function MotionLineChartStatic({ motion, shapes_acce, shapes_gyro, on_click = null }:
    { motion: Motion, on_click: CallableFunction | null, shapes_acce: any[], shapes_gyro: any[] }) {

    const [width, setWidth] = useState<number>(0);
    const [height, setHeight] = useState<number>(0);
    const divRef = useRef<HTMLDivElement>(null);



    useEffect(() => {
        const handle_resize = () => {
            if (divRef.current) {
                setWidth(divRef.current.clientWidth);
                setHeight(divRef.current.clientHeight)
            }

        }
        handle_resize()
        window.addEventListener('resize', handle_resize);
        // Cleanup
        return () => {
            window.removeEventListener('resize', handle_resize);
        };

    }, []);

    return <div ref={divRef} style={{ width: "100%", height: "60%" }}>
        <div className="line-chart" style={{ marginBottom: "1rem" }}>
            <LineChartStatic shapes={shapes_acce} on_click={on_click} x={motion.streams[0]} y={motion.streams[1]} z={motion.streams[2]} width={width} height={height / 2.5} />
        </div>
        <div className="line-chart">
            <LineChartStatic shapes={shapes_gyro} on_click={on_click} x={motion.streams[3]} y={motion.streams[4]} z={motion.streams[5]} width={width} height={height / 2.5} />
        </div>

    </div>
}

function Selector({ text, on_change }) {

    return <div className="switch-button">
        <img src={arrow_svg} className="button arrow-left" onClick={() => { on_change(true) }} />
        <div>{text}</div>
        <img src={arrow_svg} className="button arrow-right" onClick={() => { on_change(false) }} />
    </div>

}
export function RecordedMotions() {
    let [motions, set_motions] = useState<{ motion: Motion, shapes: any[], shapes_acce: any[], shapes_gyro: any[] }[]>([])
    let [motion_selected, set_motion_selected] = useState<number>(0)
    const [curr_shape, set_curr_shape] = useState<any>(null);
    const [remove_switch_state, set_remove_switch_state] = useState<boolean>(false);

    useEffect(() => {
        function handle_new_motion(str_packets) {

            set_motions(prev => [...prev, {
                motion: JSON.parse(str_packets),
                shapes: [],
                shapes_acce: [],
                shapes_gyro: []
            }])

        }

        socket.on("new_motion", handle_new_motion)
        return () => { socket.off("new_motion", handle_new_motion) }
    }, [])

    function on_motion_selection(is_left: boolean) {
        set_motion_selected((prev_motion_selected) => {
            let new_motion_selected = prev_motion_selected
            if (is_left) {
                new_motion_selected--;
                if (new_motion_selected < 0) {
                    new_motion_selected = motions.length - 1;
                }
            }
            else {
                new_motion_selected++;
                if (new_motion_selected > motions.length - 1) {
                    new_motion_selected = 0;
                }
            }


            return Number(new_motion_selected)
        })
    }
    function shapes_handle(point) {
        if (curr_shape === null) {
            let new_shape = {
                id: String(Math.floor(Math.random() * 100000)),
                type: 'line',
                x0: point.points[0].pointNumber,
                y0: -Number.MAX_SAFE_INTEGER,
                x1: point.points[0].pointNumber,
                y1: Number.MAX_SAFE_INTEGER,
                line: {
                    color: 'yellow',
                    width: 1
                }

            }
            set_curr_shape(new_shape)
            console.log("Once")

            let new_motions = [...motions]
            new_motions[motion_selected].shapes_acce = [...new_motions[motion_selected].shapes_acce, new_shape]
            new_motions[motion_selected].shapes_gyro = [...new_motions[motion_selected].shapes_gyro, new_shape]

            set_motions(new_motions)

        }
        else {

            let new_shape = {}
            new_shape["type"] = 'rect';
            new_shape["xref"] = 'x';
            new_shape["line_width"] = '0';
            new_shape["yref"] = 'paper';
            new_shape["x0"] = curr_shape.x0;
            new_shape["x1"] = point.points[0].pointNumber;
            new_shape["y0"] = 0;
            new_shape["y1"] = 1;
            new_shape["fillcolor"] = '#AF4D56';
            new_shape["opacity"] = 0.3;
            new_shape["layer"] = 'below';

            set_motions(old => {
                let new_motions = [...old]
                new_motions[motion_selected].shapes_acce = new_motions[motion_selected].shapes_acce.map((val) => { return val.id === curr_shape.id ? new_shape : val })
                new_motions[motion_selected].shapes_gyro = new_motions[motion_selected].shapes_gyro.map((val) => { return val.id === curr_shape.id ? new_shape : val })
                return new_motions
            })


            set_curr_shape(null)
        }
    }

    function shapes_remove_handle(point) {
        set_motions((old) => {
            let new_motions = [...old]

            new_motions.forEach(motion => {
                motion.shapes_acce = motion.shapes_acce.filter(shape => {
                    const x0 = shape.x0;
                    const x1 = shape.x1;
                    const pointNumber = point.points[0].pointNumber;

                    if ((typeof x0 !== 'undefined' && typeof x1 !== 'undefined') &&
                        ((x0 <= pointNumber && pointNumber <= x1) || (x1 <= pointNumber && pointNumber <= x0))) {
                        return false
                    }
                    return true
                });
                motion.shapes_gyro = motion.shapes_gyro.filter(shape => {
                    const x0 = shape.x0;
                    const x1 = shape.x1;
                    const pointNumber = point.points[0].pointNumber;

                    if ((typeof x0 !== 'undefined' && typeof x1 !== 'undefined') &&
                        ((x0 <= pointNumber && pointNumber <= x1) || (x1 <= pointNumber && pointNumber <= x0))) {
                        return false
                    }
                    return true
                });

            })

            return new_motions
        })
    }

    function on_click(point) {
        if (remove_switch_state) {
            shapes_remove_handle(point)
        }
        else {
            shapes_handle(point)
        }
    }

    function clear() {
        set_motions((old) => {
            let new_motions = [...old]
            new_motions[motion_selected].shapes_acce = []
            new_motions[motion_selected].shapes_gyro = []

            return new_motions
        })
        set_curr_shape(null)
    }

    function remove_switch() {
        set_remove_switch_state(old => { return !old })
    }
    const input_label_ref = useRef<HTMLInputElement>(null);

    let [download_icon, set_download_icon] = useState(0)
    // 0 save
    // 1 tick
    // 2 remove


    function download() {
        if (!input_label_ref.current || input_label_ref.current.value === "") {
            set_download_icon(2)
            setTimeout(() => { set_download_icon(0) }, 1000)
            return;
        }

        let msg = {}
        msg["motion"] = motions[motion_selected].motion
        msg["shapes_acce"] = motions[motion_selected].shapes_acce.map((shape) => { return { start: shape.x0, end: shape.x1, type: shape.type } })
        msg["shapes_gyro"] = motions[motion_selected].shapes_gyro.map((shape) => { return { start: shape.x0, end: shape.x1, type: shape.type } })
        msg["label"] = input_label_ref.current.value
        /*
        let msg: { shapes_packets: any[][] } = {
            shapes_packets: []
        }
        motions[motion_selected].shapes_acce.forEach((shape, index) => {
            if (shape.type == 'line') {
                return;
            }
            msg.shapes_packets[index] = []
            let min: number, max: number;
            if (shape.x0 < shape.x1) {
                min = shape.x0;
                max = shape.x1;
            }
            else {
                min = shape.x1;
                max = shape.x0;
            }

            for (let packet of motions[motion_selected].packets) {

                if (min - packet.nb_readings < 0) {
                    let copied_packet = copy_packet(packet)
                    const readings_to_copy = 0 > min ? 0 : min
                    copied_packet.press_index.fill(0, 0, readings_to_copy)
                    for (let i = 0; i < readings_to_copy; i++) {
                        copied_packet.acc_readings[i] = [0, 0, 0];
                        copied_packet.gyro_readings[i] = [0, 0, 0]
                    }
                    msg.shapes_packets[index].push(copied_packet)
                }
                max -= packet.nb_readings;
                if (max < 0) { break; }
                min -= packet.nb_readings;
            }
        })
        */

        set_download_icon(1)
        setTimeout(() => { set_download_icon(0) }, 1000)

        fetch("/save_motions", {
            method: "POST",
            body: JSON.stringify(msg),
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        });
        clear()
    }
    return <div style={{ width: "90%", height: "100%", marginRight: "5%" }}>

        {motions[motion_selected] ? <>
            <div style={{
                display: "flex", flexDirection: "row", alignItems: "center",
                justifyContent: "center"
            }}>
                Data Label
                <input type="text" className="motion-input" ref={input_label_ref} />
                <div className="download-button" onClick={download}>
                    {download_icon === 0 && <img src={save_svg} alt="" className="button" />}
                    {download_icon === 1 && <img src={done_svg} alt="" className="button" />}
                    {download_icon === 2 && <img src={x_svg} alt="" className="button" />}
                </div>
            </div>
            <MotionLineChartStatic on_click={on_click} 
            shapes_acce={motions[motion_selected].shapes_acce} 
            shapes_gyro={motions[motion_selected].shapes_gyro}
            motion={motions[motion_selected].motion} />
            <div style={{ display: "flex", flexDirection: "row", width: "100%" }}>
                <div style={{
                    width: "30%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                }} className="button" onClick={clear}>
                    Clear
                </div>
                <div style={{
                    width: "30%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                }} className={`button switch-button-remove${remove_switch_state ? "-on" : ""}`} onClick={remove_switch}>
                    Remove Switch
                </div>
                <div style={{ width: "40%" }}>
                    <Selector text={motion_selected.toString()} on_change={on_motion_selection} />
                </div>
            </div>
        </> : ""}

    </div>
}