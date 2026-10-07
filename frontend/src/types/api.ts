export interface User {
  id: number
  email: string
  is_admin: boolean
}

export interface Character {
  id: number
  name: string
  age: number
  pronouns: string
  bio: string
  profession_label: string
  is_npc: boolean
  photo_url: string | null
  created_at: string
}

export interface CharacterStats {
  posts: number
  followers: number
  following: number
}

export interface CharacterDetail extends Character {
  money: number | null
  stats: CharacterStats
  is_me: boolean
  hobbies: string[]
  is_following: boolean
  discovered_level: number
}

export interface AuthResponse {
  token: string
  user: User
}

export interface MeResponse {
  user: User
  active_character: Character | null
}

export interface World {
  city_name: string
  date: string
  time: string
  day_of_week: number
  day_name: string
  last_simulated_at: string
  last_catchup_at: string | null
}

export interface AuthorBrief {
  id: number
  name: string
  profession_label: string
  photo_url: string | null
}

export interface Post {
  id: number
  content: string
  kind: string
  created_at: string
  author: AuthorBrief
  likes_count: number
  comments_count: number
  liked_by_me: boolean
}

export interface FeedResponse {
  items: Post[]
  next_cursor: number | null
}

export interface Conversation {
  id: number
  partner: AuthorBrief
  last_message_at: string | null
  last_message_preview: string | null
}

export interface ConversationDetail extends Conversation {
  active_session_id: number | null
}

export interface Message {
  id: number
  conversation_id: number
  sender_character_id: number
  content: string
  created_at: string
  is_mine: boolean
}

export interface MessageList {
  items: Message[]
}

export interface SendMessageResponse {
  message: Message
  npc_reply: Message | null
  warning: string | null
}

export interface Comment {
  id: number
  post_id: number
  content: string
  created_at: string
  author: AuthorBrief
}

export interface LikeOut {
  liked: boolean
  likes_count: number
}

export interface FollowOut {
  following: boolean
  followers_count: number
}

export interface EventItem {
  id: number
  title: string
  description: string
  scheduled_at: string
  status: string
  kind: string
  location_id: number
  location_name: string
  host_character_id: number | null
  host_name: string
  participant_count: number
  my_status: string | null
  cancel_reason: string | null
}

export interface EventParticipant {
  character_id: number
  name: string
  status: string
  photo_url: string | null
  is_npc: boolean
}

export interface EventDetail extends EventItem {
  participants: EventParticipant[]
  am_host: boolean
}

export interface EventTurnAction {
  id: string
  label: string
  effects: Record<string, unknown>
  hint?: string
}

export interface EventTurn {
  id: number
  turn_index: number
  narrative: string
  dialogue: { speaker: string; line: string }[]
  available_actions: EventTurnAction[]
  player_action_id: string | null
  player_action_label: string | null
  created_at: string
}

export interface SessionSummary {
  id: number
  event_id: number
  status: string
  turn_count: number
  resume_count: number
  started_at: string
  ended_at: string | null
  last_activity_at: string
}

export interface SessionState {
  session: SessionSummary
  turns: EventTurn[]
  can_act: boolean
  outcome_id: number | null
}

export interface MemoryRef {
  character_id: number | null
  name: string
  memory_id: number
}

export interface Outcome {
  id: number
  session_id: number
  summary: string
  relationship_changes: unknown[]
  memories: MemoryRef[]
  social_effects: unknown[]
  future_hooks: unknown[]
  applied_at: string
}

export interface RelationshipItem {
  id: number
  other_character_id: number
  other_name: string
  other_is_npc: boolean
  familiarity: number
  friendship: number
  trust: number
  romance: number
  respect: number
  tension: number
  last_interaction_at: string | null
  updated_at: string
}

export interface MemoryItem {
  id: number
  other_character_id: number | null
  other_name: string
  category: string
  kind: string
  content: string
  importance: number
  occurred_at: string
  context: Record<string, unknown>
}

export interface MilestoneItem {
  key: string
  name: string
  description: string
  threshold: number
  count: number
  pending: boolean
  last_opportunity_at: string | null
}

export interface CatchUpPayment {
  character_id: number
  name: string
  amount: number
  job: string
  day: string
}

export interface CatchUpReport {
  elapsed_minutes: number
  from: string
  to: string
  payments: CatchUpPayment[]
  locations: number
  social: string[]
  summary: string
}

export interface CityPulsePost {
  id: number
  author_id: number
  author_name: string
  kind: string
  content: string
  created_at: string
}

export interface CityPulseEvent {
  id: number
  title: string
  status: string
  scheduled_at: string
  host_name: string
}

export interface CityPulseHighlight {
  character_id: number
  character_name: string
  kind: string
  content: string
  importance: number
  occurred_at: string
}

export interface CityPulseLocation {
  location_id: number
  location_name: string
  resident_count: number
}

export interface CityPulse {
  generated_at: string
  social_weather: string
  resident_count: number
  activity_count: number
  hot_locations: CityPulseLocation[]
  recent_posts: CityPulsePost[]
  recent_events: CityPulseEvent[]
  social_highlights: CityPulseHighlight[]
}

export interface SimulationLog {
  id: number
  ran_at: string
  kind: string
  elapsed_minutes: number
  summary: string
}

export interface NotificationItem {
  id: number
  type: string
  payload: Record<string, unknown>
  created_at: string
  read_at: string | null
}

export interface Listing<T> {
  items: T[]
}

export interface District {
  id: number
  name: string
  slug: string
  description: string
}

export interface Location {
  id: number
  name: string
  slug: string
  district_id: number
  district_name: string
  kind: string
  description: string
  opening_hours: { ranges: string[][]; closed_days: number[] } | null
  activities: string[]
}
