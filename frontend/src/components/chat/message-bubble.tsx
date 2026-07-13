import { Check, Copy, RefreshCw, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { Markdown } from "./markdown";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";
type MessageBubbleProps = {
  message: Message & { pending?: boolean };
  userInitials: string;
  onRegenerate?: () => void;
};
export function MessageBubble({ message, userInitials, onRegenerate }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const isUser = message.role === "user";
  const isStreaming = message.pending && message.role === "assistant";
  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex gap-4 animate-rise">
      {isUser ? (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-[10px] font-bold text-muted-foreground ring-1 ring-black/5">
          {userInitials}
        </div>
      ) : (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand text-brand-foreground ring-1 ring-brand/20">
          <Sparkles className="size-4" />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-sm font-semibold">
          {isUser ? "You" : "Fieldforce"}
        </div>
        {isUser ? (
          <div className="text-pretty text-sm leading-relaxed text-foreground/85">
            {message.content}
          </div>
        ) : (
          <>
            <Markdown>{message.content || ""}</Markdown>
            {isStreaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-brand/50 cursor-pulse align-middle" />
            )}
            {!isStreaming && message.content && (
              <div className="mt-3 flex items-center gap-1 opacity-0 transition-opacity group-hover/thread:opacity-100 focus-within:opacity-100 [.group\\/msg:hover_&]:opacity-100">
                <ActionButton onClick={handleCopy} label={copied ? "Copied" : "Copy"}>
                  {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                </ActionButton>
                {onRegenerate && (
                  <ActionButton onClick={onRegenerate} label="Regenerate">
                    <RefreshCw className="size-3.5" />
                  </ActionButton>
                )}
                <ActionButton
                  onClick={() => setFeedback(feedback === "up" ? null : "up")}
                  label="Helpful"
                  active={feedback === "up"}
                >
                  <ThumbsUp className="size-3.5" />
                </ActionButton>
                <ActionButton
                  onClick={() => setFeedback(feedback === "down" ? null : "down")}
                  label="Not helpful"
                  active={feedback === "down"}
                >
                  <ThumbsDown className="size-3.5" />
                </ActionButton>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
function ActionButton({
  children,
  label,
  onClick,
  active,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-1.5 py-1 text-[11px] font-medium transition-colors",
        active
          ? "bg-brand-soft text-brand"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}