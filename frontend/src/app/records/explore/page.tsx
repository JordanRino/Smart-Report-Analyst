import { Suspense } from "react";
import RecordsExplore from "@/modules/records/RecordsExplore";

export default function RecordsExplorePage() {
  return (
    <Suspense fallback={null}>
      <RecordsExplore />
    </Suspense>
  );
}
