"use client";

import { Suspense } from "react";
import MOMContent from "./MOMContent";

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <MOMContent />
    </Suspense>
  );
}