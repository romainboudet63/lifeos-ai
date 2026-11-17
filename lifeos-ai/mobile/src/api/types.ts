export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  priority: "low" | "medium" | "high";
  status: "todo" | "in_progress" | "done";
  created_at: string;
}

export interface Habit {
  id: string;
  name: string;
  category: string | null;
  target_frequency: number;
}

export interface HabitLog {
  id: string;
  date: string;
  completed: boolean;
  note: string | null;
}

export interface Goal {
  id: string;
  title: string;
  category: string | null;
  target_date: string | null;
  progress: number;
  status: "active" | "done" | "abandoned";
}

export interface CalendarEvent {
  id: string;
  external_provider: string | null;
  title: string;
  start_at: string;
  end_at: string;
  location: string | null;
}

export interface Workout {
  id: string;
  external_id: string | null;
  type: string | null;
  duration_min: number | null;
  calories: number | null;
  performed_at: string | null;
  source: string;
}

export interface WorkoutSession {
  day_label: string;
  type: string;
  duration_min: number;
  description: string;
}

export interface WorkoutWeek {
  week_number: number;
  focus: string;
  sessions: WorkoutSession[];
}

export interface WorkoutProgram {
  id: string;
  objective: string;
  title: string;
  source: "ia" | "heuristique";
  weeks: WorkoutWeek[];
  created_at: string;
}

export interface WorkoutProgramSummary {
  id: string;
  objective: string;
  title: string;
  source: "ia" | "heuristique";
  week_count: number;
  created_at: string;
}

export interface NutritionLog {
  id: string;
  description: string;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  logged_at: string;
}

export interface NutritionDailySummary {
  date: string;
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  entries: NutritionLog[];
}

export interface NutritionEstimate {
  found: boolean;
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  matched_foods: string[];
  source: "ia" | "heuristique";
}

export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  category: string | null;
  description: string | null;
  occurred_at: string;
}

export interface BudgetStatus {
  category: string;
  monthly_limit: number;
  spent_this_month: number;
  percent_used: number;
  over_budget: boolean;
}

export interface CategorySpending {
  category: string;
  total: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  reply: string;
  used_memories: string[];
}

export interface Memory {
  id: string;
  content: string;
  category: string | null;
  created_at: string;
}

export interface Nudge {
  key: string;
  view: "tasks" | "habits";
  text: string;
  warn: boolean;
}
