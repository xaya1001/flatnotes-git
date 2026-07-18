{ pkgs, ... }: {
  # 1. Channel & Packages
  channel = "stable-25.05";
  packages = [
    pkgs.python311
    pkgs.pipenv
    pkgs.nodejs_20
    pkgs.openssh
    pkgs.git
  ];

  # 2. Environment Variables
  # This 'env' block sets it globally for all shells and processes in the workspace.
  env = {
    PYTHONPATH = "server";
    FLATNOTES_PATH = "data";
  };

  # 3. VS Code Extensions
  idx.extensions = [
    "ms-python.python"       
    "Vue.volar"
    "esbenp.prettier-vscode" 
    "ms-python.debugpy"
    "vitest.explorer"
    "bradlc.vscode-tailwindcss"
    "eamodio.gitlens"
    "google.geminicodeassist"
    "ms-python.black-formatter"
  ];

  # 4. Workspace Creation Hook (First-Time Setup)
  # The 'onCreate' block runs commands only when the workspace is created.
  idx.workspace.onCreate = {
    install-backend-deps = "pipenv install --dev";
    install-frontend-deps = "npm install";
    initial-frontend-build = "npm run build";
  };
  
  # 5. Previews (Daily Workflow)
  idx.previews = {
    enable = true;
    previews = {
      # The backend Uvicorn server.
      backend = {
        command = [ "pipenv" "run" "uvicorn" "server.main:app" "--reload" "--host" "0.0.0.0" "--port" "8000" ];
        manager = "web";
      };

      # The frontend Vite development server.
      web = {
        command = [ "npm" "run" "dev" "--" "--port" "$PORT" "--host" "0.0.0.0"];
        manager = "web";
      };
    };
  };
}