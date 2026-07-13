import { useEffect, useState } from "react";
import { getAccessToken } from "@/lib/api-client";
export function useAuthStatus() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  useEffect(() => {
    const sync = () => setAuthed(Boolean(getAccessToken()));
    sync();
    window.addEventListener("ff-auth-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("ff-auth-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return authed;
}