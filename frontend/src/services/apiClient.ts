import axios, { AxiosError } from 'axios';

// Lấy URL backend từ biến môi trường hoặc fallback về localhost:8001 (tránh xung đột với các dịch vụ khác trên cổng 8000)
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // QUAN TRỌNG: Cho phép gửi và nhận cookie HttpOnly
  headers: {
    'Content-Type': 'application/json',
  },
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string | Array<{ msg: string }> }>;
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail;
      if (typeof detail === 'string') {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0 && detail[0].msg) {
        return detail.map((d) => d.msg).join(', ');
      }
    }
    if (axiosError.response?.status === 401) {
      return 'Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.';
    }
    if (axiosError.response?.status === 403) {
      return 'Bạn không có quyền thực hiện hành động này.';
    }
    if (axiosError.response?.status === 404) {
      return 'Không tìm thấy tài nguyên yêu cầu.';
    }
    if (axiosError.response?.status === 500) {
      return 'Lỗi hệ thống máy chủ. Vui lòng thử lại sau.';
    }
    if (axiosError.message === 'Network Error') {
      return 'Không thể kết nối đến máy chủ backend. Vui lòng kiểm tra dịch vụ backend.';
    }
    return axiosError.message || 'Đã có lỗi xảy ra khi gửi yêu cầu.';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Đã có lỗi không xác định xảy ra.';
}
