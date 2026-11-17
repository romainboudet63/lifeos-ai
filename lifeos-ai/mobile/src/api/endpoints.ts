import { api } from "./client";
import { User, Task, Habit, HabitLog, Goal, ChatMessage, ChatResponse, Memory, Nudge, CalendarEvent, Workout, WorkoutProgram, WorkoutProgramSummary, NutritionLog, NutritionDailySummary, NutritionEstimate, Transaction, BudgetStatus, CategorySpending } from "./types";

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    api.post<User>("/auth/register", { email, password, full_name }, { auth: false }),

  login: (email: string, password: string) =>
    api.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
      { auth: false, formBody: true }
    ),

  me: () => api.get<User>("/auth/me"),
};

export const tasksApi = {
  list: () => api.get<Task[]>("/tasks"),
  create: (title: string, priority: "low" | "medium" | "high" = "medium", dueDate?: string) =>
    api.post<Task>("/tasks", { title, priority, due_date: dueDate }),
  updateStatus: (id: string, status: Task["status"]) =>
    api.patch<Task>(`/tasks/${id}`, { status }),
  remove: (id: string) => api.delete<void>(`/tasks/${id}`),
};

export const habitsApi = {
  list: () => api.get<Habit[]>("/habits"),
  create: (name: string, category?: string, target_frequency = 7) =>
    api.post<Habit>("/habits", { name, category, target_frequency }),
  log: (habitId: string, completed = true, note?: string) =>
    api.post<HabitLog>(`/habits/${habitId}/log`, { completed, note }),
  logs: (habitId: string) => api.get<HabitLog[]>(`/habits/${habitId}/logs`),
};

export const goalsApi = {
  list: () => api.get<Goal[]>("/goals"),
  create: (title: string, category?: string, target_date?: string) =>
    api.post<Goal>("/goals", { title, category, target_date }),
  updateProgress: (id: string, progress: number) =>
    api.patch<Goal>(`/goals/${id}/progress?progress=${progress}`),
};

export const chatApi = {
  send: (message: string) => api.post<ChatResponse>("/ai/chat", { message }),
  history: () => api.get<ChatMessage[]>("/ai/chat/history"),
};

export const memoriesApi = {
  list: () => api.get<Memory[]>("/ai/memories"),
  // Le backend attend `content` en paramètre d'URL (et non dans le corps de la requête).
  add: (content: string) =>
    api.post<Pick<Memory, "id" | "content" | "category">>(`/ai/memories?content=${encodeURIComponent(content)}`),
  remove: (id: string) => api.delete<void>(`/ai/memories/${id}`),
  clear: () => api.delete<void>("/ai/memories"),
};

export const nudgesApi = {
  list: (tz?: string, dismissed: string[] = []) => {
    const params: string[] = [];
    if (tz) params.push(`tz=${encodeURIComponent(tz)}`);
    dismissed.forEach((key) => params.push(`dismissed=${encodeURIComponent(key)}`));
    return api.get<Nudge[]>(`/nudges${params.length ? `?${params.join("&")}` : ""}`);
  },
};

export const calendarApi = {
  googleStatus: () => api.get<{ connected: boolean; provider: string | null }>("/calendar/google/status"),
  googleAuthUrl: () => api.get<{ auth_url: string }>("/calendar/google/auth-url"),
  sync: (daysAhead = 14) => api.post<CalendarEvent[]>(`/calendar/sync?days_ahead=${daysAhead}`),
  list: () => api.get<CalendarEvent[]>("/calendar/events"),
  create: (title: string, startAt: string, endAt: string, location?: string) =>
    api.post<CalendarEvent>("/calendar/events", {
      title,
      start_at: startAt,
      end_at: endAt,
      location,
      push_to_google: true,
    }),
};

export const stravaApi = {
  status: () => api.get<{ connected: boolean; provider: string | null }>("/strava/status"),
  authUrl: () => api.get<{ auth_url: string }>("/strava/auth-url"),
  sync: () => api.post<Workout[]>("/strava/sync"),
  list: () => api.get<Workout[]>("/strava/workouts"),
};

export const workoutProgramApi = {
  generate: (objective: string, weeks?: number) =>
    api.post<WorkoutProgram>("/workouts/programs", { objective, weeks }),
  list: () => api.get<WorkoutProgramSummary[]>("/workouts/programs"),
  get: (id: string) => api.get<WorkoutProgram>(`/workouts/programs/${id}`),
};

export const nutritionApi = {
  list: () => api.get<NutritionLog[]>("/nutrition"),
  create: (description: string, calories?: number, protein_g?: number, carbs_g?: number, fat_g?: number) =>
    api.post<NutritionLog>("/nutrition", { description, calories, protein_g, carbs_g, fat_g }),
  daily: (forDate?: string) => api.get<NutritionDailySummary>(`/nutrition/daily${forDate ? `?for_date=${forDate}` : ""}`),
  estimate: (description: string) => api.post<NutritionEstimate>("/nutrition/estimate", { description }),
};

export const financeApi = {
  listTransactions: () => api.get<Transaction[]>("/finance/transactions"),
  createTransaction: (amount: number, category?: string, description?: string) =>
    api.post<Transaction>("/finance/transactions", { amount, category, description }),
  budgetsStatus: () => api.get<BudgetStatus[]>("/finance/budgets/status"),
  createBudget: (category: string, monthly_limit: number) =>
    api.post("/finance/budgets", { category, monthly_limit }),
  spendingByCategory: () => api.get<CategorySpending[]>("/finance/spending-by-category"),
};
