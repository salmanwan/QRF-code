# ====================================================================
# RELATIONAL CIRCUIT COMPLEXITY
# ====================================================================
import warnings
from qiskit import QuantumCircuit, transpile
warnings.filterwarnings("ignore")

print("==========================================================")
print(" IDEAL SIMULATION: RELATIONAL COMPLEXITY (LOCAL & GLOBAL)")
print("==========================================================\n")


qc_C = QuantumCircuit(3)
qc_C.h(0); qc_C.cx(0, 1)


qc_B = QuantumCircuit(3)
qc_B.ch(2, 0)   
qc_B.barrier()  
qc_B.swap(0, 2) 


basis = ['cx', 'u']
t_C = transpile(qc_C, basis_gates=basis, optimization_level=1)
t_B = transpile(qc_B, basis_gates=basis, optimization_level=1)

def count_gates(qc):
    local_g = sum(1 for inst in qc.data if len(inst.qubits) == 1 and inst.operation.name != 'barrier')
    global_g = sum(1 for inst in qc.data if len(inst.qubits) == 2 and inst.operation.name != 'barrier')
    return local_g, global_g

l_C, g_C = count_gates(t_C)
l_B, g_B = count_gates(t_B)

print(f"Frame C (Logical baseline) : {l_C} Local Gates, {g_C} Global Gates")
print(f"Frame B (Compiled Shift)   : {l_B} Local Gates, {g_B} Global Gates")
print("==========================================================")


# ====================================================================
# HARDWARE TRANSPILATION:  QPU TOPOLOGY RELATIONAL COMPLEXITY
# ====================================================================
import warnings
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService
warnings.filterwarnings("ignore")

TOKEN =  # Use the actual token string
print("Authenticating to IBM Quantum...")

service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN)
backend = service.backend("ibm_torino")
print(f"\n✅ Selected Real QPU for topology mapping: {backend.name}\n")

qc_C = QuantumCircuit(3)
qc_C.h(0); qc_C.cx(0, 1)

qc_B = QuantumCircuit(3)
qc_B.ch(2, 0)
qc_B.barrier()
qc_B.swap(0, 2)

print("Running strict compiler against real hardware coupling map...")

t_C = transpile(qc_C, backend=backend, optimization_level=0)
t_B = transpile(qc_B, backend=backend, optimization_level=0)

def count_hw_gates(qc):
    local_g = sum(1 for inst in qc.data if len(inst.qubits) == 1 and inst.operation.name != 'barrier')
    global_g = sum(1 for inst in qc.data if len(inst.qubits) == 2 and inst.operation.name != 'barrier')
    return local_g, global_g

l_C, g_C = count_hw_gates(t_C)
l_B, g_B = count_hw_gates(t_B)

print("==========================================================")
print(f" RELATIONAL COMPLEXITY (REAL HARDWARE: {backend.name})")
print("==========================================================")
print(f"Frame C (Logical baseline) : {l_C} Local Pulses, {g_C} Global Entangling Pulses")
print(f"Frame B (Compiled Shift)   : {l_B} Local Pulses, {g_B} Global Entangling Pulses")
print("==========================================================")


# ====================================================================
# SCRIPT 2: HIGH-FIDELITY HARDWARE TOMOGRAPHY (VIRTUAL SWAP)
# ====================================================================
import numpy as np
import warnings
from qiskit import QuantumCircuit
from qiskit.circuit.library import SwapGate
from qiskit.quantum_info import partial_trace, DensityMatrix, Operator
from qiskit_experiments.library import StateTomography
from qiskit_ibm_runtime import QiskitRuntimeService

warnings.filterwarnings("ignore")


TOKEN = ""
print("Authenticating to IBM Quantum...")
service = QiskitRuntimeService(channel="ibm_quantum_platform", token=TOKEN)
# Automatically picks the best, least busy hardware you have access to!
backend = service.least_busy(operational=True, simulator=False, min_num_qubits=3)
print(f"✅ Selected Real QPU: {backend.name}\n")

# --- 2. RIGOROUS RESOURCE MATH (PURE NUMPY) ---
def wootters_concurrence_sq(rho_2q):
    rho = np.asarray(rho_2q.data) if hasattr(rho_2q, 'data') else np.asarray(rho_2q)
    sysy = np.array([[0,0,0,-1], [0,0,1,0], [0,1,0,0], [-1,0,0,0]], dtype=complex)
    R = rho @ sysy @ rho.conj() @ sysy
    evals = np.sort(np.sqrt(np.maximum(np.real(np.linalg.eigvals(R)), 0.0)))[::-1]
    return max(0.0, float(evals[0] - evals[1] - evals[2] - evals[3]))**2

def local_coherence_d2(rho_1q):
    rho = np.asarray(rho_1q.data) if hasattr(rho_1q, 'data') else np.asarray(rho_1q)
    return 4.0 * (np.abs(rho[0, 1]) ** 2)

# --- 3. HARDWARE CIRCUITS (VIRTUAL SWAP APPLIED) ---
# Frame A
qc_A = QuantumCircuit(3, name="Frame_A")
qc_A.h(1); qc_A.x(2)

# Frame B (Virtual SWAP)
# We apply the alignment CX, but OMIT the physical SWAP.
# We will do the SWAP mathematically in the readout!
qc_B_virt = QuantumCircuit(3, name="Frame_B_Virtual")
qc_B_virt.h(1); qc_B_virt.x(2); qc_B_virt.cx(1, 2)

# --- 4. EXECUTE ---
SHOTS = 8192
print("-- Submitting Frame A Tomography ---")
# optimization_level=3 allows IBM to find the quietest part of the chip automatically
qst_A = StateTomography(qc_A)
qst_A.set_transpile_options(optimization_level=3)
job_A = qst_A.run(backend=backend, shots=SHOTS)
print(f"JOB ID A: {job_A.experiment_id} (Waiting...)")
rho_A = job_A.block_for_results().analysis_results("state").value

print("\n--- Submitting Frame B Tomography ---")
qst_B = StateTomography(qc_B_virt)
qst_B.set_transpile_options(optimization_level=3)
job_B = qst_B.run(backend=backend, shots=SHOTS)
print(f"JOB ID B: {job_B.experiment_id} (Waiting...")
rho_B_raw = job_B.block_for_results().analysis_results("state").value


rho_B_shifted = DensityMatrix(rho_B_raw).evolve(Operator(SwapGate()), qargs=[0, 1])

# --- 5. EXTRACT RESULTS ---
D2_A = local_coherence_d2(partial_trace(rho_A, [0, 2]))
C2_A = wootters_concurrence_sq(partial_trace(rho_A, [0]))

D2_B = local_coherence_d2(partial_trace(rho_B_shifted, [1, 2]))
C2_B = wootters_concurrence_sq(partial_trace(rho_B_shifted, [1]))

print("\n==========================================================")
print(f" HIGH-FIDELITY HARDWARE RESULTS ({backend.name})")
print("==========================================================")
print(f"FRAME A (Lab)     |  D_B^2 = {D2_A:.4f}  |  C_BC^2 = {C2_A:.4f}  |  Total = {D2_A + C2_A:.4f}")
print(f"FRAME B (Shifted) |  D_A^2 = {D2_B:.4f}  |  C_AC^2 = {C2_B:.4f}  |  Total = {D2_B + C2_B:.4f}")
print("==========================================================")


# ====================================================================
# SCRIPT 3: IDEAL NOISELESS SIMULATIONS FOR PAPER
# ====================================================================
import numpy as np
import warnings
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import partial_trace, DensityMatrix
from qiskit_aer import AerSimulator
from qiskit_experiments.library import StateTomography
warnings.filterwarnings("ignore")

print("==========================================================")
print(" PART 1: RELATIONAL COMPLEXITY (STRUCTURAL BLOAT)")
print("==========================================================\n")
qc_C = QuantumCircuit(3); qc_C.h(0); qc_C.cx(0, 1)
qc_B = QuantumCircuit(3); qc_B.ch(2, 0); qc_B.barrier(); qc_B.swap(0, 2)

t_C = transpile(qc_C, basis_gates=['cx', 'u'], optimization_level=1)
t_B = transpile(qc_B, basis_gates=['cx', 'u'], optimization_level=1)
print(f"Frame C (Logical baseline): {t_C.count_ops().get('cx', 0)} Global Gates")
print(f"Frame B (Compiled Shift):   {t_B.count_ops().get('cx', 0)} Global Gates\n")

print("==========================================================")
print(" PART 2: RESOURCE CONSERVATION (C^2 + D^2 = 1)")
print("==========================================================\n")
def wootters_concurrence_sq(rho_2q):
    rho = np.asarray(rho_2q.data) if hasattr(rho_2q, 'data') else np.asarray(rho_2q)
    sysy = np.array([[0,0,0,-1], [0,0,1,0], [0,1,0,0], [-1,0,0,0]], dtype=complex)
    R = rho @ sysy @ rho.conj() @ sysy
    evals = np.sort(np.sqrt(np.maximum(np.real(np.linalg.eigvals(R)), 0.0)))[::-1]
    return max(0.0, float(evals[0] - evals[1] - evals[2] - evals[3])) ** 2

def local_coherence_d2(rho_1q):
    rho = np.asarray(rho_1q.data) if hasattr(rho_1q, 'data') else np.asarray(rho_1q)
    return 4.0 * (np.abs(rho[0, 1]) ** 2)

backend = AerSimulator(method="density_matrix")

# Frame A
qc_A = QuantumCircuit(3); qc_A.h(1); qc_A.x(2)
rho_A = StateTomography(qc_A).run(backend).block_for_results().analysis_results("state").value

# Frame B (Using exact math)
qc_B2 = QuantumCircuit(3); qc_B2.h(1); qc_B2.x(2); qc_B2.cx(1, 2); qc_B2.swap(0, 1)
rho_B = StateTomography(qc_B2).run(backend).block_for_results().analysis_results("state").value

# Evaluate
D2_A = local_coherence_d2(partial_trace(rho_A, [0, 2]))
C2_A = wootters_concurrence_sq(partial_trace(rho_A, [0]))
D2_B = local_coherence_d2(partial_trace(rho_B, [1, 2]))
C2_B = wootters_concurrence_sq(partial_trace(rho_B, [1]))

print(f"FRAME A | D_B^2 = {D2_A:.4f} | C_BC^2 = {C2_A:.4f} | Total = {D2_A + C2_A:.4f}")
print(f"FRAME B | D_A^2 = {D2_B:.4f} | C_AC^2 = {C2_B:.4f} | Total = {D2_B + C2_B:.4f}")