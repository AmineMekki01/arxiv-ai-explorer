declare namespace NodeJS {
  interface ProcessEnv {
    REACT_APP_API_URL?: string;
  }
}

declare var process: {
  env: NodeJS.ProcessEnv;
};
