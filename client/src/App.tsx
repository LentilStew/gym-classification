import { MotionRecording } from "./motion_recording.tsx";
import {MotionReview} from "./motion_review/motion_review.tsx"
import React, { StrictMode, useState } from "react";

const str_to_page = {
  "motion_recognition": MotionRecording,
  "motion_review":MotionReview
};

function App() {
  const [PageSelected, set_page_selected] = useState<any>(()=>str_to_page["motion_recognition"]);

  function switch_page(page:string) {
    set_page_selected(()=>str_to_page[page])
  }

  return (
    <StrictMode>
      <PageSelected switch_page={switch_page} />
    </StrictMode>
  );
}

export default App;