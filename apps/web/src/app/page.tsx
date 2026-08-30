import { Masthead } from "@/components/Masthead";
import { Ceiling } from "@/components/Ceiling";
import { DayShape } from "@/components/DayShape";
import { WeekendMirror } from "@/components/WeekendMirror";
import { Reliability } from "@/components/Reliability";
import { EvidenceMap } from "@/components/EvidenceMap";
import { Limits } from "@/components/Limits";
import { Close } from "@/components/Close";

export default function Page() {
  return (
    <>
      <Masthead />
      <main id="findings">
        <Ceiling />
        <DayShape />
        <WeekendMirror />
        <Reliability />
        <EvidenceMap />
        <Limits />
      </main>
      <Close />
    </>
  );
}
