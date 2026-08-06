import Markdown from "react-markdown";

/**
 * Inline markdown for one-liners: prerequisites, pitfalls, verify criteria.
 * Playbook authors write `code` there as naturally as in a step body, and
 * showing raw backticks in one place while rendering them in another looks
 * like a bug. The paragraph wrapper is dropped so it stays inline.
 */
export function Inline({ children }: { children: string }) {
  return (
    <Markdown
      components={{
        p: ({ children: content }) => <>{content}</>,
      }}
    >
      {children}
    </Markdown>
  );
}
