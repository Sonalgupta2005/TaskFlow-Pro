import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
});

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

export const updateTask = async (taskId: string, updateData: Partial<Task>): Promise<Task> => {
  const { data } = await apiClient.put(`/tasks/${taskId}`, updateData);
  return data;
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
  task_id: string;
  suggested_prereq_id: string;
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

