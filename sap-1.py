BUS = 0x00

class ProgramCounter:
	def __init__(self):
		self.pc = 0x00

	def enable(self):
		global BUS
		BUS = self.pc

	def clock(self):
		print("increasing PC:")
		self.pc += 1
		print(self.pc)

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

class BRegister(Loadable):
	pass

class InstructionRegister(Loadable, Enablable):
	def __init__(self):
		super().__init__()
		self.enable_mask = 0xF
		self.load_mask = 0xFF

class MAR(Loadable):
	def __init__(self):
		self.load_mask = 0xF
	
class RAM(Enablable):
	def __init__(self, mar):
		self.mar = mar
		self.memory = [0x00] * 0xF

	def enable(self):
		global BUS
		BUS = self.memory[self.mar.value]

class OutputRegister(Loadable):
	pass

class Instruction:
	init_code = [
		# (enables, loads, clocks, subtracts, end_instr)
		("pc", 0, 0, 0, 0),
		(0, "mar", 0, 0, 0),
		("ram", 0, 0, 0, 0),
		(0, "ir", 0, 0, 0),
		(0, 0, "pc", 0, 0),
	]
	def __init__(self, microcode_instructions):
		self.microcode_instructions = self.init_code + microcode_instructions
		self.microcode_instructions += [(0, 0, 0, 0, 1)]

	def __getitem__(self, item):
		return self.microcode_instructions[item]

class Control:
	def __init__(self, enable_pins, load_pins):
		self.enable_pins = enable_pins
		self.load_pins = load_pins
		self.microcode_ptr = 0

		self.instructions = [
			Instruction([
				("ir", 0, 0, 0, 0),
				(0, "accumulator", 0, 0, 0),
			]),
			Instruction([
				("ir", 0, 0, 0, 0),
				(0, "b_register", 0, 0, 0),
				("adder", 0, 0, 0, 0),
				(0, "accumulator", 0, 0 ,0),
			])
		]

	def clock(self):
		# put program counter on the bus
		# load address from memory
		# put memory on bus
		# load instruction from bus
		# increase program counter
		# execute instruction
		end_instr = self.execute_microcode(self.instructions[self.enable_pins["ir"].value >> 4][self.microcode_ptr])
		if end_instr:
			self.microcode_ptr = 0
		else:
			self.microcode_ptr = self.microcode_ptr + 1

	def execute_microcode(self, microcode_instruction) -> bool:
		enables, loads, clocks, subtracts, end_instr = microcode_instruction

		print(f"Enabling: {enables}, loading: {loads}, clocking: {clocks}, subtracts: {subtracts}")
		print(f"BUS: 0x{BUS:02x}")
		if end_instr:
			print()

		if enables:
			self.enable_pins[enables].enable()
		if loads:
			self.load_pins[loads].load()
		if clocks:
			self.enable_pins[clocks].clock()
		self.enable_pins["adder"].set_subtract(subtracts)
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
		"accumulator": ENABLE_PINS["accumulator"],
		"b_register": b_register,
		"output": OutputRegister(),
	}

	# Program theh computer :-)
	ENABLE_PINS["ram"].memory[0] = 0x05
	ENABLE_PINS["ram"].memory[1] = 0x14
	ENABLE_PINS["ram"].memory[2] = 0x14

	controller = Control(ENABLE_PINS, LOAD_PINS)

	for i in range(40):
		controller.clock()

if __name__ == "__main__":
	main()

