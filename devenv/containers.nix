{
  config,
  pkgs,
  lib,
  ...
}:

{
  containers.python-app = {
    name = "python-app";
    version = "1.0.0";

    enableLayerDeduplication = true;

    copyToRoot = lib.cleanSourceWith {
      filter =
        name: type:
        let
          baseName = baseNameOf name;
        in
        !(type == "directory" && (baseName == ".devenv" || baseName == ".venv" || baseName == ".git"));
      src = ./..;
    };
    layers = [
      {
        deps = with pkgs; [
          cacert
          # Pulls the package from your global `languages.python` option configuration automatically
          config.languages.python.package
        ];
      }
      {
        deps = [ pkgs.uv ];
      }
    ];

    startupCommand = "uv run --no-dev --frozen python main.py";
  };
}
