import { useEffect, useRef, useState } from "react";
import { ArrowUp, Paperclip, Square } from "lucide-react";
import { cn } from "@/lib/utils";
type ComposerProps = {
  onSubmit: (value: string) => void;
  disabled?: boolean;
  streaming?: boolean;
  onStop?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
};
export function Composer({
  onSubmit,
  disabled,
  streaming,
  onStop,
  placeholder = "Ask a question about your documents…",
  autoFocus = true,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 260) + "px";
  }, [value]);
  const canSend = value.trim().length > 0 && !disabled;
  const handleSend = () => {
    if (!canSend) return;
    onSubmit(value.trim());
    setValue("");
    requestAnimationFrame(() => ref.current?.focus());
  };
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pb-4 sm:px-6 sm:pb-6">
      <div className="group relative rounded-2xl bg-surface shadow-sm ring-1 ring-black/5 transition-shadow focus-within:ring-2 focus-within:ring-brand/40">
        <textarea
          ref={ref}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={placeholder}
          rows={1}
          className="w-full resize-none rounded-2xl bg-transparent px-4 pt-4 pb-2 text-sm leading-relaxed outline-none placeholder:text-muted-foreground/70"
          style={{ minHeight: 56 }}
        />
        <div className="flex items-center justify-between px-2.5 pb-2.5">
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Attach (coming soon)"
              disabled
            >
              <Paperclip className="size-4" />
            </button>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70 sm:block">
              <kbd className="rounded border border-hairline bg-muted px-1 py-px font-sans text-[10px]">
                Enter
              </kbd>{" "}
              to send · <kbd className="rounded border border-hairline bg-muted px-1 py-px font-sans text-[10px]">
                Shift+Enter
              </kbd>{" "}
              newline
            </span>
            {streaming ? (
              <button
                type="button"
                onClick={onStop}
                className="flex size-8 items-center justify-center rounded-lg bg-foreground text-background ring-1 ring-black/10 transition-all hover:opacity-90"
                title="Stop"
              >
                <Square className="size-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                className={cn(
                  "flex size-8 items-center justify-center rounded-lg ring-1 transition-all",
                  canSend
                    ? "bg-brand text-brand-foreground ring-brand/20 hover:opacity-90"
                    : "cursor-not-allowed bg-muted text-muted-foreground ring-black/5",
                )}
                title="Send"
              >
                <ArrowUp className="size-4" />
              </button>
            )}
          </div>
        </div>
      </div>
      <p className="mt-2 text-center text-[10px] text-muted-foreground/70">
        Fieldforce RAG may produce inaccurate interpretations. Verify critical citations.
      </p>
    </div>
  );
}