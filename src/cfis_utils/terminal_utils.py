# Standard libraries
import os
import platform
import subprocess
import sys
import locale
from typing import Optional, Union
from dataclasses import dataclass
import tempfile
# Local imports
from . import TimeUtils, LoggerUtils

class TerminalUtils:
    """Utility class for terminal operations and command execution."""
    
    _is_windows: Optional[bool] = None

    @dataclass
    class CommandResult:
        """Data class to store command execution results."""
        execution_time: float
        stdout: str
        stderr: str
        exit_code: int
        command: str
        cwd: Optional[str] = None

        def is_success(self) -> bool:
            """Check if the command executed successfully."""
            return self.exit_code == 0

        def __str__(self) -> str:
            """String representation of command result with clear formatting."""

            # Format some fields
            status = "SUCCESS" if self.is_success() else "FAILED"
            execution_time = TimeUtils.format_time(self.execution_time)
            cwd = self.cwd or os.getcwd()

            # Define a separator
            SEP = "=" * 50

            # Init the output string
            result = []
            result.append(SEP)
            result.append("COMMAND EXECUTION DETAILS")
            result.append(SEP)
            result.append(f"Command   : {self.command}")
            result.append(f"Status    : {status}")
            result.append(f"Exit Code : {self.exit_code}")
            result.append(f"Duration  : {execution_time}")
            result.append(f"CWD       : {cwd}")
            
            # Add output if exists
            if self.stdout:
                result.extend([
                    SEP,
                    "COMMAND OUTPUT",
                    SEP,
                    self.stdout.strip()
                ])
            
            # Add errors if exists
            if self.stderr:
                result.extend([
                    SEP,
                    "ERROR OUTPUT",
                    SEP,
                    self.stderr.strip()
                ])
            
            # Add final separator
            result.append(SEP)

            # Return the formatted string
            return "\n".join(result)

    @staticmethod
    def run_command(
        command: Union[str, list],
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[dict] = None,
        interactive: bool = False,
    ) -> 'TerminalUtils.CommandResult':
        """
        Run a command and return its execution details.
        Uses temporary files instead of PIPE for output capture (to avoid some PIPE limitations).

        Args:
            command (Union[str, list]): The command to execute
            cwd (Optional[str]): Working directory for command execution
            timeout (Optional[float]): Maximum time in seconds to wait
            env (Optional[dict]): Environment variables to set
            interactive (bool): Whether the command needs interactive terminal access

        Returns:
            CommandResult: Object containing execution details
        """
        with TimeUtils.timer() as get_elapsed:
            try:
                if isinstance(command, list):
                    command = ' '.join(command)

                if interactive:
                    # For interactive commands, don't capture output
                    process = subprocess.run(
                        command,
                        cwd=cwd,
                        shell=True,
                        env=env,
                        timeout=timeout
                    )
                    elapsed_time = get_elapsed()
                    return TerminalUtils.CommandResult(
                        execution_time=elapsed_time,
                        stdout="",
                        stderr="",
                        exit_code=process.returncode,
                        command=command,
                        cwd=cwd
                    )
                else:
                    # Create temporary files for stdout and stderr
                    with tempfile.NamedTemporaryFile(mode='w+') as stdout_file, \
                        tempfile.NamedTemporaryFile(mode='w+') as stderr_file:
                        
                        stdout_path = stdout_file.name
                        stderr_path = stderr_file.name
                        
                        # Modify the command to append all output to our temp files
                        # Use parentheses to group compound commands
                        if any(op in command for op in ['&&', '||', '|', ';']):
                            command = f"( {command} ) >> {stdout_path} 2>> {stderr_path}"
                        else:
                            command = f"{command} >> {stdout_path} 2>> {stderr_path}"
                        
                        process = subprocess.run(
                            command,
                            cwd=cwd,
                            shell=True,
                            env=env,
                            timeout=timeout
                        )
                        
                        # Seek to beginning of files to read output
                        stdout_file.seek(0)
                        stderr_file.seek(0)
                        
                        # Read output from temporary files
                        stdout = stdout_file.read() or ""
                        stderr = stderr_file.read() or ""
                        
                        # Get elapsed time
                        elapsed_time = get_elapsed()

                        # Return
                        return TerminalUtils.CommandResult(
                            execution_time=elapsed_time,
                            stdout=LoggerUtils.remove_color_codes(stdout),
                            stderr=LoggerUtils.remove_color_codes(stderr),
                            exit_code=process.returncode,
                            command=command,
                            cwd=cwd
                        )
            except subprocess.TimeoutExpired as e:
                return TerminalUtils.CommandResult(
                    execution_time=get_elapsed(),
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    exit_code=-1,
                    command=command,
                    cwd=cwd
                )
            except Exception as e:
                return TerminalUtils.CommandResult(
                    execution_time=get_elapsed(),
                    stdout="",
                    stderr=str(e),
                    exit_code=-1,
                    command=command,
                    cwd=cwd
                )
        
    @staticmethod
    def get_terminal_encoding() -> str:
        """
        Get the current terminal encoding in a cross-platform way.
        
        Returns:
            str: The terminal encoding (e.g., 'utf-8', 'cp1252', 'cp437')
        """
        try:
            # Try to get encoding from stdout first
            if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
                return sys.stdout.encoding.lower()
            
            # Fallback to locale encoding
            encoding = locale.getpreferredencoding()
            if encoding:
                return encoding.lower()
            
            # Final fallback based on platform
            if platform.system().lower() == 'windows':
                return 'cp1252'  # Common Windows encoding
            else:
                return 'utf-8'   # Common Unix encoding
                
        except Exception:
            # Ultimate fallback
            return 'utf-8'

    @staticmethod
    def clear() -> None:
        """
        Clear the terminal screen in a cross-platform way.
        Uses 'cls' for Windows and 'clear' for Unix-like systems.
        """
        try:
            if TerminalUtils._is_windows is None:
                TerminalUtils._is_windows = platform.system().lower() == 'windows'
            
            os.system('cls' if TerminalUtils._is_windows else 'clear')
        except Exception:
            # Fallback to printing newlines if clear fails
            print('\n' * 100)

# Example usage
if __name__ == "__main__":
    print(TerminalUtils.get_terminal_encoding())