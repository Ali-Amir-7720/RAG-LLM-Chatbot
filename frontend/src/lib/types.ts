export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};
export type User = {
  id: string;
  username: string;
  email: string;
  profile_picture?: string | null;
  created_at: string;
  updated_at: string;
};
export type AuthResponse = {
  user: User;
  tokens: TokenPair;
};
export type Conversation = {
  id: string;
  user_id: string;
  title: string;
  model_name: string;
  system_prompt?: string | null;
  generation_config: Record<string, unknown>;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
};
export type Message = {
  id: string;
  conversation_id: string;
  parent_message_id?: string | null;
  role: "system" | "user" | "assistant";
  content: string;
  model_name?: string | null;
  token_count?: number | null;
  generation_time?: number | null;
  is_helpful?: boolean | null;
  feedback_text?: string | null;
  created_at: string;
};
