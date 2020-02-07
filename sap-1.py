import collections

BUS = 0x00

class ProgramCounter:
	def __init__(self):
		self.pc = 0x00

	def enable(self):
		global BUS
		BUS = self.pc

	def load(self):
		self.pc = BUS

	def clock(self):
		self.pc += 1

	def reset(self):
		self.pc = 0


class Loadable:
	def __init__(self, load_mask=0xFF):
		self.value = 0x00
		self.load_mask = load_mask

	def load(self):
		self.value = BUS & self.load_mask

class Enablable:
	def __init__(self, enable_mask=0xFF):
		self.enable_mask = enable_mask

	# already expects a value object
	def enable(self):
		global BUS
		BUS = self.value & self.enable_mask

class Accumulator(Loadable, Enablable):
	def __init__(self):
		super().__init__()
		self.enable_mask = 0xFF
		self.load_mask = 0xFF

class BRegister(Loadable):
	pass

class Adder:
	def __init__(self, accumulator, b_register):
		self.accumulator = accumulator
		self.b_register = b_register
		self.subtract = False

	def set_subtract(self, subtract=True):
		self.subtract = subtract

	def enable(self):
		global BUS
		if self.subtract:
			BUS = self.accumulator.value - self.b_register.value
		else:
			BUS = self.accumulator.value + self.b_register.value

class InstructionRegister(Loadable, Enablable):
	def __init__(self):
		super().__init__()
		self.enable_mask = 0xF
		self.load_mask = 0xFF

class MAR(Loadable):
	def __init__(self):
		self.load_mask = 0xF
	
class RAM(Loadable, Enablable):
	def __init__(self, mar):
		self.mar = mar
		self.memory = [0x00] * 0x10

	def enable(self):
		global BUS
		BUS = self.memory[self.mar.value]

	def load(self):
		global BUS
		self.memory[self.mar.value] = BUS & 0xFF

class OutputRegister(Loadable):
	pass

# A microcode instruction, this defines which devices get to enable, load, etc.
MI = collections.namedtuple(
		"MI",
		("enables", "loads", "clocks", "subtracts", "end_instr", "halt"),
		defaults=(0,0,0,0,0,0)
)

class Instruction:
	init_code = [
		# (enables, loads, clocks, subtracts, end_instr)
		MI("pc", 0, 0, 0, 0),
		MI(0, "mar", 0, 0, 0),
		MI("ram", 0, 0, 0, 0),
		MI(0, "ir", 0, 0, 0),
		MI(0, 0, "pc", 0, 0),
	]
	def __init__(self, name, microcode_instructions):
		self.name = name
		self.microcode_instructions = self.init_code + microcode_instructions
		self.microcode_instructions += [MI(0, 0, 0, 0, 1)]

	def __getitem__(self, item):
		return self.microcode_instructions[item]

class Control:
	def __init__(self, enable_pins, load_pins):
		self.enable_pins = enable_pins
		self.load_pins = load_pins
		self.halted = False
		self.microcode_ptr = 0

		self.instructions = [
			Instruction("NOP", [
			]),
			Instruction("LDA", [
				MI("ir", 0, 0, 0, 0),
				MI(0, "mar", 0, 0, 0),
				MI("ram", 0, 0, 0, 0),
				MI(0, "accumulator", 0, 0, 0),
			]),
			Instruction("ADD", [
				MI("ir", 0, 0, 0, 0),
				MI(0, "mar", 0, 0, 0),
				MI("ram", 0, 0, 0, 0),
				MI(0, "b_register", 0, 0, 0),
				MI("adder", 0, 0, 0, 0),
				MI(0, "accumulator", 0, 0 ,0),
			]),
			Instruction("SUB", [
				MI("ir", 0, 0, 0, 0),
				MI(0, "b_register", 0, 0, 0),
				MI("adder", 0, 0, 1, 0),
				MI(0, "accumulator", 0, 0 ,0),
			]),
			Instruction("STA", [
				MI("ir", 0, 0, 0, 0),
				MI(0, "mar", 0, 0, 0),
				MI("accumulator", 0, 0, 0 ,0),
				MI(0, "ram", 0, 0, 0),
			]),
			Instruction("LDI", [
				MI("ir", 0, 0, 0, 0),
				MI(0, "accumulator", 0, 0, 0),
			]),
			Instruction("JMP", [
				MI(enables="ir"),
				MI(loads="pc"),
			]),
			Instruction("E7", [
			]),
			Instruction("E8", [
			]),
			Instruction("E9", [
			]),
			Instruction("EA", [
			]),
			Instruction("EB", [
			]),
			Instruction("EC", [
			]),
			Instruction("ED", [
			]),
			Instruction("OUT", [
			]),
			Instruction("HLT", [
				MI(halt=1)
			]),
		]

	def clock(self):
		instr = self.enable_pins["ir"].value >> 4
		value = self.enable_pins["ir"].value & 0xF 
		if self.microcode_ptr == 0:
			print(self.instructions[instr].name, f"0x{value:02x}")
		end_instr = self.execute_microcode(self.instructions[instr][self.microcode_ptr])
		if end_instr:
			self.microcode_ptr = 0
		else:
			self.microcode_ptr = self.microcode_ptr + 1

		return self.halted

	def execute_microcode(self, microcode_instruction) -> bool:
		enables, loads, clocks, subtracts, end_instr, halt = microcode_instruction

		print(f"Enabling: {enables}, loading: {loads}, clocking: {clocks}, subtracts: {subtracts}, halt: {halt}")
		print(f"BUS: 0x{BUS:02x} ->", end="")

		if enables:
			self.enable_pins[enables].enable()
		if loads:
			self.load_pins[loads].load()
		if clocks:
			self.enable_pins[clocks].clock()
		if halt:
			self.halted = True
		self.enable_pins["adder"].set_subtract(subtracts)

		print(f"0x{BUS:02x}")

		if end_instr:
			print()

		return end_instr


def main():
	mar = MAR()
	accumulator = Accumulator()
	b_register = BRegister()
	ENABLE_PINS = {
		"pc": ProgramCounter(),
		"ir": InstructionRegister(),
		"ram": RAM(mar),
		"accumulator": accumulator,
		"adder": Adder(accumulator, b_register),
	}
	LOAD_PINS = {
		"pc": ENABLE_PINS["pc"],
		"ir": ENABLE_PINS["ir"],
		"mar": mar,
		"ram": ENABLE_PINS["ram"],
		"accumulator": ENABLE_PINS["accumulator"],
		"b_register": b_register,
		"output": OutputRegister(),
	}

	# Program theh computer :-)
	ENABLE_PINS["ram"].memory[0] = 0x55 # LDI 5
	ENABLE_PINS["ram"].memory[1] = 0x4f # STA 15
	ENABLE_PINS["ram"].memory[2] = 0x54 # LDI 4
	ENABLE_PINS["ram"].memory[3] = 0x2f # ADD 15
	ENABLE_PINS["ram"].memory[4] = 0x4e # STA 14
	ENABLE_PINS["ram"].memory[5] = 0xF0 # HLT
	ENABLE_PINS["ram"].memory[6] = 0x61 # JMP $1

	controller = Control(ENABLE_PINS, LOAD_PINS)

	while not controller.clock():
		for i in range(16):
			print("%02x" % ENABLE_PINS["ram"].memory[i], end=" ")
		print("")

if __name__ == "__main__":
	main()

