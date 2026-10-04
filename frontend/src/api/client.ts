import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export type TaskStatus = 'backlog' | 'in_progress' | 'review' | 'done';

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  position: number;
  duration_days: number;
  planned_start: string;
  start_date: string;
  end_date: string;
  actual_start_date: string | null;
  actual_end_date: string | null;
  created_at: string;
  blocked: boolean;
  is_critical: boolean;
  version: number;
}

export interface Dependency {
  prerequisite_id: string;
  dependent_id: string;
}

export const fetchTasks = async (): Promise<Task[]> => {
  const { data } = await apiClient.get('/tasks');
  return data;
};

export const createTask = async (task: Omit<Task, 'id' | 'start_date' | 'end_date' | 'blocked' | 'is_critical' | 'version' | 'status' | 'position' | 'actual_start_date' | 'actual_end_date' | 'created_at'>): Promise<Task> => {
  const { data } = await apiClient.post('/tasks', task);
  return data;
};

export const updateTask = async (taskId: string, updateData: Partial<Task>): Promise<Task> => {
  const { data } = await apiClient.put(`/tasks/${taskId}`, updateData);
  return data;
};

export const deleteTask = async (taskId: string): Promise<void> => {
  await apiClient.delete(`/tasks/${taskId}`);
};

export const fetchDependencies = async (): Promise<Dependency[]> => {
  const { data } = await apiClient.get('/dependencies');
  return data;
};

export const createDependency = async (prerequisiteId: string, dependentId: string): Promise<Dependency> => {
  const { data } = await apiClient.post('/dependencies', { prerequisite_id: prerequisiteId, dependent_id: dependentId });
  return data;
};

export const removeDependency = async (prerequisiteId: string, dependentId: string): Promise<void> => {
  await apiClient.delete(`/dependencies?prerequisite_id=${prerequisiteId}&dependent_id=${dependentId}`);
};

export interface DependencySuggestion {
  id: number;
  prerequisite_id: string;
  dependent_id: string;
  confidence: string;
  rationale: string;
  status: string;
}

export const fetchSuggestions = async (): Promise<DependencySuggestion[]> => {
  const { data } = await apiClient.post('/suggestions');
  return data;
};

export const acceptSuggestion = async (id: number): Promise<void> => {
  await apiClient.post(`/suggestions/${id}/accept`);
};

export const dismissSuggestion = async (id: number): Promise<void> => {
  await apiClient.post(`/suggestions/${id}/dismiss`);
};

export const fetchDraftSuggestions = async (title: string, description: string, id: string): Promise<DependencySuggestion[]> => {
  const { data } = await apiClient.post('/auto-suggest-draft', { title, description, id });
  return data;
};

export const login = async (username: string, password: string) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  const { data } = await apiClient.post('/auth/token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return data;
};

export const register = async (username: string, password: string) => {
  const { data } = await apiClient.post('/auth/register', { username, password });
  return data;
};

export const seedData = async () => {
  const { data } = await apiClient.post('/seed');
  return data;
};

