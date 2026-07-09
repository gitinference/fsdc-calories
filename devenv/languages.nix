{ config, pkgs, ... }:
let
  # Evaluates to true if the dev profile is being actively used
  isDev = config.profiles.dev.module or null != null;
in
{
  languages.python = {
    enable = true;
    package = pkgs.python312;
    venv.enable = true;

    # Dynamically toggled based on active profile
    lsp.enable = isDev;
    uv = {
      enable = true;
      sync.enable = isDev;
    };
  };
}
