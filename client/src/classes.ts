export interface Header {
    HZ: number;
    accelerometer_len: number;
    accelerometer_order: string;
    accelerometer_start: number;
    header_size: number
    is_little_endian: string;
    nb_readings: number;
    packet_index: number;
    quaternion_len: number;
    quaternion_order: string;
    quaternion_start: number;
}

export class motion_segment {
    quaternion_array: Uint16Array;
    accelerometer_array: Uint16Array;
    header_obj: Header;
    decoder: TextDecoder;

    constructor(buffer: Uint8Array, header_len: number) {
        //Header stuff
        this.decoder = new TextDecoder('utf-8');
        let header = this.decoder.decode(buffer.slice(0, 300))
        let tmp: any = {}

        header.split("\n").map((row: string) => row.split(":")).map(
            (row: string[]) => row.length === 2 ? tmp[row[0]] = row[1] : null)

        this.header_obj = tmp

        function isNumericRegex(str: string) {
            return /^\d+$/.test(str);
        }

        for (let val in this.header_obj) {
            if (isNumericRegex(this.header_obj[val] as string)) {
                this.header_obj[val] = parseInt(this.header_obj[val] as string)
            }
        }

        //body stuff this.header_obj["quaternion_start"] , this.header_obj["quaternion_len"]
        this.quaternion_array = new Uint16Array(buffer.buffer,this.header_obj.quaternion_start , this.header_obj.nb_readings*this.header_obj.quaternion_order.length)
        this.accelerometer_array = new Uint16Array(buffer.buffer,this.header_obj.accelerometer_start , this.header_obj.nb_readings*this.header_obj.accelerometer_order.length)
    }
}

export class motion {
    motion_segments: Array<motion_segment>;

    constructor(buffer: ArrayBuffer, buffer_segment_len: number, header_len: number) {
        this.motion_segments = []
        for (let start = 0; start < buffer.byteLength; start += buffer_segment_len) {
            this.motion_segments.push(new motion_segment(new Uint8Array(buffer, start, buffer_segment_len), header_len))
        }
    }
}