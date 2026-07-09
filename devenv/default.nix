# devenv/default.nix
{ ... }:

{
  imports = [
    ./scripts.nix
    ./pre-commit.nix
    ./languages.nix

    # As you add more files in the future, just uncomment them here:
    # ./services.nix
    # ./containers.nix
  ];
}
