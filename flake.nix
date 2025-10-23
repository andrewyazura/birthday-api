{
  description = "birthday api";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self, nixpkgs, pyproject-nix, uv2nix, pyproject-build-systems, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
      overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

      python = pkgs.python310;
      pythonBase =
        pkgs.callPackage pyproject-nix.build.packages { inherit python; };

      pythonSet = pythonBase.overrideScope (pkgs.lib.composeManyExtensions [
        pyproject-build-systems.overlays.wheel
        overlay
        (final: prev: {
          peewee = prev.peewee.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or [ ])
              ++ [ final.setuptools final.wheel ];
          });
        })
      ]);
    in {
      devShells.${system}.default = let
        editableOverlay =
          workspace.mkEditablePyprojectOverlay { root = "$REPO_ROOT"; };
        editablePythonSet = pythonSet.overrideScope editableOverlay;

        virtualenv = editablePythonSet.mkVirtualEnv "birthday-api-dev-env"
          workspace.deps.all;
      in pkgs.mkShell {
        packages = [ virtualenv pkgs.uv ];

        env = {
          UV_NO_SYNC = "1";
          UV_PYTHON = editablePythonSet.python.interpreter;
          UV_PYTHON_DOWNLOADS = "never";
        };

        shellHook = ''
          unset PYTHONPATH
          export REPO_ROOT=$(git rev-parse --show-toplevel)
        '';
      };

      packages.${system} = let
        inherit (pkgs.callPackage pyproject-nix.build.util { }) mkApplication;
      in {
        default = mkApplication {
          venv =
            pythonSet.mkVirtualEnv "birthday-api-env" workspace.deps.default;
          package = pythonSet."birthday-api";
        };
      };

      nixosModules.default = { config, pkgs, lib, ... }:
        let cfg = config.services.birthday-api;
        in {
          options.services.birthday-api = {
            enable = lib.mkEnableOption "Enable birthday api";
            configFile = lib.mkOption {
              type = lib.types.nullOr
                (lib.types.either lib.types.path lib.types.str);
              default = null;
              description =
                "Path to the configuration file for the birthday api";
              example = "/var/lib/birthday-api/config.ini";
            };
          };

          config = lib.mkIf cfg.enable {
            users.users.birthday-api = {
              description = "birthday api user";
              isSystemUser = true;
              group = "birthday-api";
            };
            users.groups.birthday-api = { };

            systemd.services.birthday-api = {
              description = "birthday api service";
              after = [ "network.target" ];
              wants = [ "network-online.target" ];
              wantedBy = [ "multi-user.target" ];

              serviceConfig = {
                User = "birthday-api";
                Group = "birthday-api";

                Environment = lib.optional (cfg.configFile != null)
                  "CONFIG_FILE_PATH=${cfg.configFile}";

                ExecStart =
                  "${self.packages.${system}.default}/bin/birthday-api";

                Type = "simple";
                Restart = "on-failure";
              };
            };
          };
        };
    };
}
