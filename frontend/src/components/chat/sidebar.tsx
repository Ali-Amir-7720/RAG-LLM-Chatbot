import { Link, useNavigate, useParams } from "@tanstack/react-router";
import {
  ChevronsLeft,
  LogOut,
  MoreHorizontal,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { usePinned } from "@/hooks/use-pinned";
import { logout } from "@/lib/auth";
import { deleteConversation, renameConversation } from "@/lib/chat";
import type { Conversation, User } from "@/lib/types";
type SidebarProps = {
  conversations: Conversation[];
  user: User | null;
  onChanged: () => void;
  onNewChat: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
};
export function Sidebar({
  conversations,
  user,
  onChanged,
  onNewChat,
  collapsed,
  onToggleCollapse,
}: SidebarProps) {
  const nav = useNavigate();
  const params = useParams({ strict: false }) as { conversationId?: string };
  const activeId = params.conversationId;
  const { toggle, isPinned } = usePinned();
  const [query, setQuery] = useState("");
  const [renaming, setRenaming] = useState<{ id: string; title: string } | null>(null);
  const [deleting, setDeleting] = useState<Conversation | null>(null);
  const { pinnedList, recentList } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? conversations.filter((c) => c.title.toLowerCase().includes(q))
      : conversations;
    return {
      pinnedList: filtered.filter((c) => isPinned(c.id)),
      recentList: filtered.filter((c) => !isPinned(c.id)),
    };
  }, [conversations, isPinned, query]);
  async function handleRename() {
    if (!renaming) return;
    try {
      await renameConversation(renaming.id, renaming.title.trim() || "Untitled");
      toast.success("Renamed");
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Rename failed");
    } finally {
      setRenaming(null);
    }
  }
  async function handleDelete() {
    if (!deleting) return;
    try {
      await deleteConversation(deleting.id);
      toast.success("Deleted");
      if (activeId === deleting.id) nav({ to: "/" });
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  }
  async function handleLogout() {
    await logout();
    toast.success("Signed out");
    nav({ to: "/auth" });
  }
  if (collapsed) {
    return (
      <aside className="flex w-14 shrink-0 flex-col items-center gap-2 border-r border-hairline bg-sidebar py-3">
        <button
          onClick={onToggleCollapse}
          className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          title="Expand sidebar"
        >
          <ChevronsLeft className="size-4 rotate-180" />
        </button>
        <button
          onClick={onNewChat}
          className="rounded-lg bg-foreground p-2 text-background shadow-sm transition-colors hover:opacity-90"
          title="New chat"
        >
          <Plus className="size-4" />
        </button>
      </aside>
    );
  }
  return (
    <>
      <aside className="flex w-64 shrink-0 flex-col border-r border-hairline bg-sidebar">
        <div className="flex flex-col gap-3 p-3">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex size-6 items-center justify-center rounded bg-brand text-[10px] font-bold text-brand-foreground">
                FF
              </div>
              <span className="text-sm font-semibold tracking-tight">Fieldforce</span>
            </Link>
            <button
              onClick={onToggleCollapse}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Collapse sidebar"
            >
              <ChevronsLeft className="size-4" />
            </button>
          </div>
          <button
            onClick={onNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-foreground px-3 py-2 text-sm font-medium text-background shadow-sm ring-1 ring-black/10 transition-all hover:opacity-90 active:scale-[0.98]"
          >
            <Plus className="size-4" />
            New chat
          </button>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
              placeholder="Search history"
              className="h-8 border-none bg-muted pl-8 text-xs shadow-none focus-visible:ring-1 focus-visible:ring-brand/40"
            />
          </div>
        </div>
        <nav className="ff-scroll flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
          {pinnedList.length > 0 && (
            <>
              <SectionLabel>Pinned</SectionLabel>
              {pinnedList.map((c) => (
                <ConversationRow
                  key={c.id}
                  conversation={c}
                  active={c.id === activeId}
                  pinned
                  onPinToggle={() => toggle(c.id)}
                  onRename={() => setRenaming({ id: c.id, title: c.title })}
                  onDelete={() => setDeleting(c)}
                />
              ))}
            </>
          )}
          {recentList.length > 0 ? (
            <>
              <SectionLabel className={pinnedList.length ? "pt-3" : ""}>Recent</SectionLabel>
              {recentList.map((c) => (
                <ConversationRow
                  key={c.id}
                  conversation={c}
                  active={c.id === activeId}
                  pinned={isPinned(c.id)}
                  onPinToggle={() => toggle(c.id)}
                  onRename={() => setRenaming({ id: c.id, title: c.title })}
                  onDelete={() => setDeleting(c)}
                />
              ))}
            </>
          ) : pinnedList.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-muted-foreground">
              {query ? "No matches." : "No conversations yet."}
            </div>
          ) : null}
        </nav>
        <div className="flex items-center gap-3 border-t border-hairline p-3">
          <div className="flex size-8 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground ring-1 ring-black/5">
            {(user?.username ?? "?").slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium">{user?.username ?? "—"}</p>
            <p className="truncate text-[10px] text-muted-foreground">{user?.email ?? ""}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            title="Sign out"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </aside>
      {/* Rename dialog */}
      <AlertDialog open={!!renaming} onOpenChange={(o: boolean) => !o && setRenaming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rename conversation</AlertDialogTitle>
            <AlertDialogDescription>Give this chat a clearer title.</AlertDialogDescription>
          </AlertDialogHeader>
          <Input
            autoFocus
            value={renaming?.title ?? ""}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setRenaming((r) => (r ? { ...r, title: e.target.value } : r))
            }
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && handleRename()}
          />
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRename}>Save</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {/* Delete confirm */}
      <AlertDialog open={!!deleting} onOpenChange={(o: boolean) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleting?.title}” and its messages will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70",
        className,
      )}
    >
      {children}
    </div>
  );
}
function ConversationRow({
  conversation,
  active,
  pinned,
  onPinToggle,
  onRename,
  onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  pinned: boolean;
  onPinToggle: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  return (
    <Link
      to="/c/$conversationId"
      params={{ conversationId: conversation.id }}
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
        active
          ? "bg-muted font-medium text-foreground"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
    >
      {pinned ? (
        <div className="size-1.5 shrink-0 rounded-full bg-brand" />
      ) : (
        <div className="size-1.5 shrink-0 rounded-full bg-muted-foreground/30" />
      )}
      <span className="min-w-0 flex-1 truncate">{conversation.title || "Untitled"}</span>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.preventDefault()}
            className="opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
          >
            <MoreHorizontal className="size-3.5 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" onClick={(e: React.MouseEvent) => e.preventDefault()}>
          <DropdownMenuItem onSelect={onPinToggle}>
            {pinned ? (
              <>
                <PinOff className="mr-2 size-3.5" /> Unpin
              </>
            ) : (
              <>
                <Pin className="mr-2 size-3.5" /> Pin
              </>
            )}
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onRename}>
            <Pencil className="mr-2 size-3.5" /> Rename
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onSelect={onDelete}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 size-3.5" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </Link>
  );
}
