declare module 'axios' {
  export interface AxiosRequestConfig {
    baseURL?: string;
    timeout?: number;
    headers?: any;
    params?: any;
  }

  export interface AxiosResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: any;
    config: AxiosRequestConfig;
  }

  export interface AxiosError {
    response?: AxiosResponse;
    request?: any;
    message: string;
  }

  export interface AxiosInstance {
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    interceptors: {
      request: {
        use(onFulfilled?: (config: any) => any, onRejected?: (error: any) => any): void;
      };
      response: {
        use(onFulfilled?: (response: any) => any, onRejected?: (error: any) => any): void;
      };
    };
  }

  export interface AxiosStatic extends AxiosInstance {
    create(config?: AxiosRequestConfig): AxiosInstance;
  }
  
  const axios: AxiosStatic;
  export default axios;
}
