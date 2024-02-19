export type PacketHeader = {
    device_id: number
    timestamp_sec: number;
    timestamp_nsec: number;
    timestamp_ms: number;
    gyro_sensitivity: number;
    streams_order: string;
    acc_sensitivity: number;
    nb_readings: number;
    packet_index: number;
    press_index: number[];
    hz: number;
    session_id: string;
}
export type TrackerSettings = {
    quaternion_row_len: number;
    accelerometer_row_len: number;
    gyro_row_len: number;
    buffer_max_size: number;
    hz: number;
    readings_per_packet: number;
    stream_port: number;
    session_id: string;
};

export type Packet = {
    streams: number[][];
    header: PacketHeader;
}

export type Motion = {
    streams: number[][];
    header: TrackerSettings;
}

export function copy_packet(packet: Packet): Packet {
    return {
        streams: packet.streams.map(s=>[...s]),
        header: {
            device_id: packet.header.device_id,
            timestamp_sec: packet.header.timestamp_sec,
            timestamp_nsec: packet.header.timestamp_nsec,
            timestamp_ms: packet.header.timestamp_ms,
            gyro_sensitivity: packet.header.gyro_sensitivity,
            streams_order: packet.header.streams_order,
            acc_sensitivity: packet.header.acc_sensitivity,
            nb_readings: packet.header.nb_readings,
            packet_index: packet.header.packet_index,
            hz: packet.header.hz,
            session_id: packet.header.session_id,
            press_index: [...packet.header.press_index]
        }
    };
}