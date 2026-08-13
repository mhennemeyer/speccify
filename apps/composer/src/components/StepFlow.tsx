import type { Selection, SkillStep } from "../types";

interface Props {
  steps: SkillStep[];
  selection: Selection;
  onSelect: (title: string) => void;
}

const NODE_HEIGHT = 44;
const NODE_GAP = 14;
const NODE_WIDTH = 210;
const LEFT = 16;

/**
 * The workflow at a glance: one node per inferred step, in order. A long skill
 * is hard to hold in your head as a wall of markdown — this is the map next to
 * the territory. Clicking a node selects the step.
 *
 * Hand-drawn SVG rather than a diagram library: the layout is a single column,
 * and a dependency-free viewer is worth more than generic graph support.
 */
export function StepFlow({ steps, selection, onSelect }: Props) {
  const height = steps.length * NODE_HEIGHT + (steps.length - 1) * NODE_GAP;
  const selectedTitle = selection.kind === "step" ? selection.title : null;

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
        const isSelected = step.title === selectedTitle;
        return (
          <g key={step.title} role="listitem">
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
              className={`flow-node${isSelected ? " selected" : ""}`}
              onClick={() => onSelect(step.title)}
            >
              <rect x={LEFT} y={y} width={NODE_WIDTH} height={NODE_HEIGHT} rx={8} />
              <text x={LEFT + 12} y={y + 18}>
                {step.number ?? index + 1}.{" "}
                {step.title.length > 24 ? `${step.title.slice(0, 23)}…` : step.title}
              </text>
              <text className="flow-meta" x={LEFT + 12} y={y + 34}>
                {step.verify ? "has a verify step" : "\u00a0"}
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
