import type { PlaybookStep, Selection } from "../types";

interface Props {
  steps: PlaybookStep[];
  selection: Selection;
  onSelect: (selection: Selection) => void;
}

const NODE_HEIGHT = 44;
const NODE_GAP = 14;
const NODE_WIDTH = 210;
const LEFT = 16;

/**
 * The workflow at a glance: one node per step, in order, with the delegated
 * ones marked. Long playbooks are hard to hold in your head as a list — this is
 * the map next to the territory. Clicking a node selects the step.
 *
 * Hand-drawn SVG rather than a diagram library: the layout is a single column,
 * and a dependency-free viewer is worth more than generic graph support.
 */
export function StepFlow({ steps, selection, onSelect }: Props) {
  const height = steps.length * NODE_HEIGHT + (steps.length - 1) * NODE_GAP;
  const selectedStepId = selection.kind === "step" ? selection.stepId : null;

  return (
    <svg
      className="step-flow"
      viewBox={`0 0 ${NODE_WIDTH + LEFT * 2} ${height}`}
      width={NODE_WIDTH + LEFT * 2}
      height={height}
      role="list"
      aria-label="Workflow steps"
    >
      {steps.map((step, index) => {
        const y = index * (NODE_HEIGHT + NODE_GAP);
        const isSelected = step.id === selectedStepId;
        return (
          <g key={step.id} role="listitem">
            {index > 0 ? (
              <line
                className="flow-edge"
                x1={LEFT + NODE_WIDTH / 2}
                y1={y - NODE_GAP}
                x2={LEFT + NODE_WIDTH / 2}
                y2={y}
                markerEnd="url(#flow-arrow)"
              />
            ) : null}
            <g
              className={`flow-node${isSelected ? " selected" : ""}${
                step.uses ? " delegated" : ""
              }`}
              onClick={() => onSelect({ kind: "step", stepId: step.id })}
            >
              <rect x={LEFT} y={y} width={NODE_WIDTH} height={NODE_HEIGHT} rx={8} />
              <text x={LEFT + 12} y={y + 18}>
                {index + 1}. {step.title.length > 24 ? `${step.title.slice(0, 23)}…` : step.title}
              </text>
              <text className="flow-meta" x={LEFT + 12} y={y + 34}>
                {step.uses ? "delegated" : step.id}
                {step.assets.length > 0 ? " · asset" : ""}
                {step.verify ? " · verify" : ""}
              </text>
            </g>
          </g>
        );
      })}
      <defs>
        <marker
          id="flow-arrow"
          viewBox="0 0 8 8"
          refX="6"
          refY="4"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M 0 0 L 8 4 L 0 8 z" className="flow-arrow-head" />
        </marker>
      </defs>
    </svg>
  );
}
