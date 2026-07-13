import { FileText, MessageSquare, Sparkles, Zap } from "lucide-react";
const SUGGESTIONS = [
  { icon: FileText, text: "Summarize the key findings across my uploaded reports." },
  { icon: Sparkles, text: "What are the top risks flagged in the latest audit?" },
  { icon: Zap, text: "Compare the vendor terms between Apex and Vertex." },
  { icon: MessageSquare, text: "Draft an executive brief from the Q4 documents." },
];
export function EmptyState({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-6 pb-8">
      <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-brand text-brand-foreground shadow-sm ring-1 ring-brand/20">
        <Sparkles className="size-6" />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">How can I help today?</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Ask anything grounded in your documents.
      </p>
      <div className="mt-8 grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, text }) => (
          <button
            key={text}
            onClick={() => onPick(text)}
            className="group flex items-start gap-3 rounded-xl border border-hairline bg-surface p-4 text-left text-sm text-foreground/80 shadow-xs transition-all hover:-translate-y-px hover:border-brand/30 hover:shadow-sm"
          >
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover:bg-brand-soft group-hover:text-brand">
              <Icon className="size-4" />
            </div>
            <span className="pt-1 leading-snug">{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}