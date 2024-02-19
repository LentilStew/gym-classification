import React, { useState, useEffect, StrictMode, useRef, useCallback } from 'react'
import { socket } from "./socket.ts"
import { PacketHeader } from './types.ts';
import Plot from 'react-plotly.js';
import { RecordedMotions } from "./RecordedMotions/RecordedMotions.tsx"
import "./App.css"

function MotionLineChart({ x, y, z, ts, curr_ts, selected, width = 300, height = 300 }) {
  const [data, setData] = useState<Object[]>([]);
  const [shapes, setShapes] = useState<Object[]>([]);


  const request_ref: any = useRef()


  const last = useRef<number>(0)
  const animate = useCallback((time) => {
    let last_index = ts.findIndex(ts => ts > (curr_ts + time))
    if (last_index < 0) { request_ref.current = requestAnimationFrame(animate); return; }
    if (last.current === last_index) { request_ref.current = requestAnimationFrame(animate); return; }
    last.current = last_index

    let packet_start = last_index - 900
    if (packet_start < 0) { packet_start = 0 }

    setData([
      {
        y: y.slice(packet_start, last_index),
        type: 'scatter',
        mode: 'lines',
        name: 'y',
        line: { 'width': .9 },

      },
      {
        y: z.slice(packet_start, last_index),
        type: 'scatter',
        mode: 'lines',
        name: 'z',
        line: { 'width': .9 },

      },
      {
        y: x.slice(packet_start, last_index),
        type: 'scatter',
        mode: 'lines',
        name: 'x',
        line: { 'width': .9 },

      },
    ]);

    setShapes(_old_shapes => {
      const new_shapes: Object[] = [];
      let curr_shape = {}
      selected.slice(packet_start, last_index).forEach((value, index) => {
        if (value === "0" && Object.keys(curr_shape).length !== 0) {
          curr_shape["x1"] = index
          new_shapes.push(curr_shape)
          curr_shape = {}
        }
        if (value === "1" && Object.keys(curr_shape).length === 0) {
          curr_shape["type"] = 'rect';
          curr_shape["xref"] = 'x';
          curr_shape["line_width"] = '0';
          curr_shape["yref"] = 'paper';
          curr_shape["x0"] = index;
          curr_shape["y0"] = 0;
          curr_shape["y1"] = 1;
          curr_shape["fillcolor"] = '#AF4D56';
          curr_shape["opacity"] = 0.3;
          curr_shape["layer"] = 'below';
        }
      });
      if (Object.keys(curr_shape).length !== 0) {
        curr_shape["x1"] = selected.length - 1
        new_shapes.push(curr_shape)
      }
      return new_shapes
    })


    request_ref.current = requestAnimationFrame(animate);
  }, [ts, curr_ts])

  useEffect(() => {
    request_ref.current = requestAnimationFrame(animate);


    return () => cancelAnimationFrame(request_ref.current);
  }, [animate]);
  const colors = ['#f3cec9', '#a262a9', '#182844'];
  const colors_name = ['y', 'z', 'x'];

  return <>
    <Plot data={data}
      layout={{
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        width: width,
        height: height,
        font: {
          color: "#F7F6F7"
        },
        colorway: colors,
        xaxis: {
          range: [0, 900],
          autorange: false,
          showticklabels: false,
          zeroline: false,
          showgrid: false

        },
        yaxis: {
          range: [-32767, 32767],
          autorange: false,
          showticklabels: false,
          zeroline: false,
          showgrid: false

        },
        shapes: shapes,

        margin: {
          t: 40,
          l: 20,
          r: 20,
          b: 0,
        },
        showlegend: false

      }}
      config={{
        displayModeBar: false
        , staticPlot: true,

      }}

    />

    <div style={{ display: "flex", flexDirection: "row" }}>
      {

        colors.map((color, index) => {
          return <div style={{
            width: "2rem",
            height: "1rem",
            backgroundColor: `${color}`,
            color: "#0E0F12"
          }}
            key={index}
          >
            {colors_name[index]}

          </div>

        })
      }
    </div >
  </>;
};



export function PacketTsContainer({ }) {

  let data_points_limit = 1200;
  const [data_xyz, set_data_xyz] = useState<number[][][]>([[[], [], []], [[], [], []]])

  const [ts, set_ts] = useState<number[]>([])
  const [press_index, set_press_index] = useState<number[]>([])
  const [width, setWidth] = useState<number>(0);
  const [height, setHeight] = useState<number>(0);

  const start_time = useRef<number>(0)
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



  useEffect(() => {
    const handleNewPacket = (str_packet: string) => {
      let msg: {
        header: PacketHeader,
        streams: number[][]
      } = JSON.parse(str_packet)

      let packet: PacketHeader = msg["header"];

      let streams: number[][] = msg["streams"]
      let packet_start_ts = (packet.timestamp_sec * 1000 + Math.floor(packet.timestamp_nsec / 1e6))
      start_time.current = packet_start_ts - window.performance.now();

      set_data_xyz((prev) => {
        let acc_array = prev[0]
        acc_array[0] = [...acc_array[0], ...streams[0]]
        acc_array[1] = [...acc_array[1], ...streams[1]]
        acc_array[2] = [...acc_array[2], ...streams[2]]


        if (acc_array[0].length > data_points_limit) {
          acc_array[0] = acc_array[0].slice(acc_array[0].length - data_points_limit, undefined);
          acc_array[1] = acc_array[1].slice(acc_array[1].length - data_points_limit, undefined);
          acc_array[2] = acc_array[2].slice(acc_array[2].length - data_points_limit, undefined);
        }

        let gyro_array = prev[1]
        gyro_array[0] = [...gyro_array[0],...streams[3]]
        gyro_array[1] = [...gyro_array[1],...streams[4]]
        gyro_array[2] = [...gyro_array[2],...streams[5]]


        if (gyro_array[0].length > data_points_limit) {
          gyro_array[0] = gyro_array[0].slice(gyro_array[0].length - data_points_limit, undefined);
          gyro_array[1] = gyro_array[1].slice(gyro_array[1].length - data_points_limit, undefined);
          gyro_array[2] = gyro_array[2].slice(gyro_array[2].length - data_points_limit, undefined);
        }

        return [acc_array, gyro_array];
      })

      set_ts((prev) => {
        for (let i = 0; i < packet.nb_readings; i++) {
          prev.push(packet_start_ts + (1000 / packet.hz) * i);
        }

        if (prev.length > data_points_limit) {
          prev = prev.slice(prev.length - data_points_limit, undefined);
        }

        return [...prev];
      });

      set_press_index(prev => {
        if (prev.length > data_points_limit) {
          prev = prev.slice(prev.length - data_points_limit, undefined);
        }
        return [...prev, ...packet.press_index]
      })
        
    };

    socket.on('new_packet', handleNewPacket)

    return () => {
      socket.off("new_packet", handleNewPacket)
    };
  }, []);


  return (
    <div ref={divRef} style={
      {
        height: "100%",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        width: "100%",
      }
    }>
      <div style={{ position: 'relative', margin: "1rem", marginTop: "0", outline: "white 1px", backgroundColor: "var(--color-black)" }}>
        <MotionLineChart x={data_xyz[0][0]} y={data_xyz[0][1]} z={data_xyz[0][2]} selected={press_index} width={width / 2.3} height={height * .8} ts={ts} curr_ts={start_time.current} />
        <div style={{ position: 'absolute', top: '10px', left: '10px', color: 'white', fontSize: "1.5rem" }}>
          Accelerometer
        </div>
      </div>
      <div style={{ position: 'relative', margin: "1rem", marginTop: "0", backgroundColor: "var(--color-black)" }} >
        <MotionLineChart x={data_xyz[1][0]} y={data_xyz[1][1]} z={data_xyz[1][2]} selected={press_index} width={width / 2.3} height={height * .8} ts={ts} curr_ts={start_time.current} />
        <div style={{ position: 'absolute', top: '10px', left: '10px', color: 'white', fontSize: "1.5rem" }}>
          Gyroscope
        </div>
      </div>
    </div >
  );
}

export function MotionRecording({ switch_page }) {
  return <div className='motion-recognition-body'>
    <span style={{ fontSize: "5rem", paddingLeft: "1rem", display: "flex" }}>
      Motion Recognition
      <div className='button' style={{ marginLeft: "auto", marginRight: "3rem", fontSize: "2rem" }} onClick={() => switch_page("motion_review")}>
        motion review
      </div>
    </span>
    <div style={{ marginLeft: "1.5vw", width: "97vw", height: "90vh", display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gridTemplateRows: "repeat(8, 1fr)" }}>
      <div style={{
        gridColumnStart: "1",
        gridColumnEnd: "7",
        gridRowStart: "1",
        gridRowEnd: "3",
      }}>
        <PacketTsContainer />
      </div>
      <div></div>

      <div style={{
        gridColumnStart: "5",
        gridColumnEnd: "7",
        gridRowStart: "3",
        gridRowEnd: "9",
      }}>
        <RecordedMotions />
      </div>
    </div>
  </div>
}