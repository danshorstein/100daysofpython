"""A small, strict BrainFuck interpreter used to test snake.bf headlessly.

Semantics (mirrored exactly by the JS interpreter in index.html):
  - 8-bit cells with wraparound, tape of 30000 cells
  - `,` with no input available reads 0 (the web shim feeds one byte per game tick)
  - unmatched brackets are a build error
"""

from __future__ import annotations


class NeedInput(Exception):
    """Raised when the program executes `,` and the input queue is empty
    and the interpreter was created with block_on_input=True."""


class BF:
    def __init__(self, code: str, tape_len: int = 30000, block_on_input: bool = False):
        self.code = [c for c in code if c in "+-<>[],."]
        self.jumps = self._match(self.code)
        self.tape = bytearray(tape_len)
        self.ptr = 0
        self.ip = 0
        self.out: list[int] = []
        self.inq: list[int] = []
        self.steps = 0
        self.block_on_input = block_on_input

    @staticmethod
    def _match(code: list[str]) -> dict[int, int]:
        stack, jumps = [], {}
        for i, c in enumerate(code):
            if c == "[":
                stack.append(i)
            elif c == "]":
                if not stack:
                    raise SyntaxError(f"unmatched ] at {i}")
                j = stack.pop()
                jumps[i], jumps[j] = j, i
        if stack:
            raise SyntaxError(f"unmatched [ at {stack[-1]}")
        return jumps

    def feed(self, *bytes_: int) -> None:
        self.inq.extend(b & 0xFF for b in bytes_)

    @property
    def halted(self) -> bool:
        return self.ip >= len(self.code)

    def run(self, max_steps: int = 200_000_000) -> str:
        """Run until halt, input starvation (block_on_input), or step budget.
        Returns 'halt' | 'input' | 'budget'."""
        code, tape, jumps = self.code, self.tape, self.jumps
        ip, ptr, budget = self.ip, self.ptr, max_steps
        n = len(code)
        while ip < n:
            if budget <= 0:
                self.ip, self.ptr = ip, ptr
                return "budget"
            c = code[ip]
            if c == "+":
                tape[ptr] = (tape[ptr] + 1) & 0xFF
            elif c == "-":
                tape[ptr] = (tape[ptr] - 1) & 0xFF
            elif c == ">":
                ptr += 1
            elif c == "<":
                ptr -= 1
                if ptr < 0:
                    raise IndexError("tape pointer went negative")
            elif c == "[":
                if tape[ptr] == 0:
                    ip = jumps[ip]
            elif c == "]":
                if tape[ptr] != 0:
                    ip = jumps[ip]
            elif c == ".":
                self.out.append(tape[ptr])
            elif c == ",":
                if self.inq:
                    tape[ptr] = self.inq.pop(0)
                elif self.block_on_input:
                    self.ip, self.ptr = ip, ptr
                    return "input"
                else:
                    tape[ptr] = 0
            ip += 1
            budget -= 1
            self.steps += 1
        self.ip, self.ptr = ip, ptr
        return "halt"

    def output_text(self) -> str:
        return "".join(chr(b) for b in self.out)


def run_bf(code: str, inputs: list[int] | None = None, max_steps: int = 200_000_000):
    m = BF(code)
    if inputs:
        m.feed(*inputs)
    status = m.run(max_steps)
    return m, status
