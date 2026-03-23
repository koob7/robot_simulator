import numpy as np
from typing import Tuple
import math
import enum

import logging

logger = logging.getLogger(__name__)

D1 = 104.0   # mm (d1)
A2 = 270.0   # mm (a2)
D4 = 300.0   # mm (d4)
D6 = 63.4    # mm (d6)

MAX_ROBOT_TILT = A2 + D4 + D6
MAX_ROBOT_WRIST_TILT = A2 + D4 

ARM_SAFE_DISTANCE_TO_OBJECT = 25.0 # mm (minimalna odległość ramienia od obiektu, aby uniknąć kolizji)

# Wszystkie jednostki w mm, kąty w radianach (do obliczeń)
ROBOT_DH_PARAMS = [
    # (a_i, alpha_i, d_i)
    (0,      np.pi/2,  D1),   # 1: d1
    (A2,     0,         0),   # 2: a2
    (0,      np.pi/2,   0),   # 3
    (0,     -np.pi/2,  D4),   # 4: d4
    (0,      np.pi/2,   0),   # 5
    (0,      0,        D6),   # 6: d6
]

def dh_matrix(a, alpha, d, theta):
    ca, sa = np.cos(alpha), np.sin(alpha)
    ct, st = np.cos(theta), np.sin(theta)
    return np.array([
        [ct, -st*ca,  st*sa, a*ct],
        [st,  ct*ca, -ct*sa, a*st],
        [0,      sa,     ca,    d],
        [0,       0,      0,    1]
    ])

def mat4_mul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    if A.shape != (4, 4) or B.shape != (4, 4):
        raise ValueError("wrong matrix size")
    return A @ B

def pose_from_transform(T: np.ndarray, degrees: bool = True) -> tuple[float, float, float, float, float, float]:

    T = np.asarray(T, dtype=float)
    if T.shape != (4, 4):
        raise ValueError("wrong matrix size")

    x, y, z = T[0, 3], T[1, 3], T[2, 3]
    R = T[:3, :3]


    den = np.sqrt(R[0, 0] ** 2 + R[0, 1] ** 2)

    b_ang = np.arctan2(R[0, 2], den)
    a_ang = np.arctan2(-R[1, 2], R[2, 2])
    c_ang = np.arctan2(-R[0, 1], R[0, 0])


    if degrees:
        
        a_out = a_ang * 180 / np.pi
        b_out = b_ang * 180 / np.pi
        c_out = c_ang * 180 / np.pi
    else:
        a_out, b_out, c_out = a_ang, b_ang, c_ang

    return float(x), float(y), float(z), float(a_out), float(b_out), float(c_out) # obrót wokół ZYX

def calculate_ik(x: float, y: float, z: float, phi_in: float, beta_in: float, psi_in: float) -> tuple[float, float, float, float, float, float]:
    

    epsilon = 0.001

    #to prevent singularities
    phi_in += epsilon
    beta_in += epsilon
    psi_in += epsilon
    
    # Konwersja kątów ze stopni na radiany
    phi = phi_in*np.pi/180
    beta = beta_in*np.pi/180
    psi = psi_in*np.pi/180

    c_alfa, s_alfa = np.cos(phi), np.sin(phi)
    c_beta, s_beta = np.cos(beta), np.sin(beta)
    c_delta, s_delta = np.cos(psi), np.sin(psi)

    em = np.eye(3)
    P = np.array([
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
    ])


    #XYZ
    em[0, 0] = c_beta * c_delta
    em[0, 1] = -c_beta * s_delta
    em[0, 2] = s_beta

    em[1, 0] = c_alfa * s_delta + c_delta * s_alfa * s_beta
    em[1, 1] = c_alfa * c_delta - s_alfa * s_beta * s_delta
    em[1, 2] = -s_alfa * c_beta

    em[2, 0] = s_alfa * s_delta - c_alfa * c_delta * s_beta
    em[2, 1] = c_delta * s_alfa + c_alfa * s_beta * s_delta
    em[2, 2] = c_alfa * c_beta

    # wyrównanie układów współrzędnych względem siebie
    em = em @ P

    # Pozycja nadgarstka
    Wx = x - D6 * em[0, 2]
    Wy = y - D6 * em[1, 2]
    Wz = z - D6 * em[2, 2]
    r = np.sqrt(Wx * Wx + Wy * Wy)
    s = Wz - D1

    theta = [0.0] * 6

    # theta[0] - pierwsza oś
    theta[0] = np.arctan2(Wy, Wx)
    
    # theta[2] - trzecia oś
    cos_theta2 = (r * r + s * s - A2 * A2 - D4 * D4) / (2 * A2 * D4)
    theta[2] = np.arctan2(-np.sqrt(1 - cos_theta2 * cos_theta2), cos_theta2)
    
    # theta[1] - druga oś
    k1 = A2 + D4 * np.cos(theta[2])
    k2 = D4 * np.sin(theta[2])
    theta[1] = np.arctan2(s, r) - np.arctan2(k2, k1)
    theta[2] += np.pi / 2


    #nx sx ax
    #ny sy ay
    #nz sz az

    ax = em[2, 2]*np.sin(theta[1]+theta[2]) + em[0, 2]*np.cos(theta[1]+theta[2])*np.cos(theta[0]) + em[1, 2]*np.cos(theta[1]+theta[2])*np.sin(theta[0])
    ay = em[0, 2]*np.sin(theta[0]) - em[1, 2]*np.cos(theta[0])
    az = em[0, 2]*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - em[2, 2]*np.cos(theta[1] + theta[2]) + em[1, 2]*np.sin(theta[1] + theta[2])*np.sin(theta[0])
    sz = em[0, 1]*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - em[2, 1]*np.cos(theta[1] + theta[2]) + em[1, 1]*np.sin(theta[1] + theta[2])*np.sin(theta[0])
    nz = em[0, 0]*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - em[2, 0]*np.cos(theta[1] + theta[2]) + em[1, 0]*np.sin(theta[1] + theta[2])*np.sin(theta[0])


    theta[3] = np.arctan2(ay,ax)
    theta[4] = np.arctan2(np.sqrt(ax*ax+ay*ay),az)
    theta[5] = np.arctan2(sz, -nz)
    
    
    for i in range(6):
        theta[i] = theta[i]*180/np.pi
        logger.debug(f"theta[{i+1}] = {theta[i]:.2f} degrees")

    return tuple(theta)

def calculate_fk(angle_0: float, angle_1: float, angle_2: float, angle_3: float, angle_4: float, angle_5: float) -> Tuple[float, float, float, float, float, float]:
        epsilon = 0.001

        #to prevent singularities
        angle_0 += epsilon
        angle_1 += epsilon
        angle_2 += epsilon
        angle_3 += epsilon
        angle_4 += epsilon
        angle_5 += epsilon

        dh = np.array([np.eye(4) for _ in range(6)])
        tr = np.array([np.eye(4) for _ in range(6)])

        axis_values = [angle_0, angle_1, angle_2, angle_3, angle_4, angle_5]

        for i in range(6):
            dh[i] = dh_matrix(ROBOT_DH_PARAMS[i][0], ROBOT_DH_PARAMS[i][1], ROBOT_DH_PARAMS[i][2], math.radians(axis_values[i]))

        tr[0] = dh[0]
        for i in range(1,6):
            tr[i] = mat4_mul(tr[i-1], dh[i])

        pos = 0, 0, 0, 0, 0, 0

        for i in range(0,6):
            pos2 = pose_from_transform(tr[i], degrees=True)
            x, y, z, a, b, c = pos2
            logger.debug(f"Joint {i+1} pos: x={x:.2f}, y={y:.2f}, z={z:.2f}, a={a:.2f}, b={b:.2f}, c={c:.2f}")
            pos = pos2


        P = np.array([
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [1, 0, 0, 0],
            [0, 0, 0, 1]
        ])

        tr[5] = tr[5] @ P

        pos = pose_from_transform(tr[5], degrees=True)
        return pos

class ValidErrorCode(enum.Enum):
    VALID = 0
    TARGET_POSE_TOO_CLOSE = 1
    TARGET_POSE_TOO_FAR = 2
    WRIST_POSE_TOO_CLOSE = 3
    WRIST_POSE_TOO_FAR = 4
    WRONG_ANGLES = 5

    def text(self) -> str:
        if self == ValidErrorCode.VALID:
            return("Valid")
        elif self == ValidErrorCode.TARGET_POSE_TOO_CLOSE:
            return("Target to close")
        elif self == ValidErrorCode.TARGET_POSE_TOO_FAR:
            return("Target to far")
        elif self == ValidErrorCode.WRIST_POSE_TOO_CLOSE:
            return("Wrist to close")
        elif self == ValidErrorCode.WRIST_POSE_TOO_FAR:
            return("Wrist to far")
        elif self == ValidErrorCode.WRONG_ANGLES:
            return("Wrong angles")


def valid_pose(x, y, z, roll, pitch, yaw) -> ValidErrorCode:

    if math.sqrt(x**2 + y**2) < 62.0 + ARM_SAFE_DISTANCE_TO_OBJECT and z > 0 - ARM_SAFE_DISTANCE_TO_OBJECT and z < 145 + ARM_SAFE_DISTANCE_TO_OBJECT: #nie można wejść do walca przy podstawie
        return ValidErrorCode.TARGET_POSE_TOO_CLOSE

    validation_z = z - D1

    cuurrent_tilt = math.sqrt(x**2 + y**2 + validation_z**2)

    if cuurrent_tilt > MAX_ROBOT_TILT:
        return ValidErrorCode.TARGET_POSE_TOO_FAR

    # Konwersja kątów ze stopni na radiany
    phi = roll*np.pi/180
    beta = pitch*np.pi/180
    psi = yaw*np.pi/180

    c_alfa, s_alfa = np.cos(phi), np.sin(phi)
    c_beta, s_beta = np.cos(beta), np.sin(beta)
    c_delta, s_delta = np.cos(psi), np.sin(psi)

    em = np.eye(3)
    P = np.array([
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
    ])


    #XYZ
    em[0, 0] = c_beta * c_delta
    em[0, 1] = -c_beta * s_delta
    em[0, 2] = s_beta

    em[1, 0] = c_alfa * s_delta + c_delta * s_alfa * s_beta
    em[1, 1] = c_alfa * c_delta - s_alfa * s_beta * s_delta
    em[1, 2] = -s_alfa * c_beta

    em[2, 0] = s_alfa * s_delta - c_alfa * c_delta * s_beta
    em[2, 1] = c_delta * s_alfa + c_alfa * s_beta * s_delta
    em[2, 2] = c_alfa * c_beta

    # wyrównanie układów współrzędnych względem siebie
    em = em @ P

    # Pozycja nadgarstka
    Wx = x - D6 * em[0, 2]
    Wy = y - D6 * em[1, 2]
    Wz = z - D6 * em[2, 2]
    validation_Wz = validation_z - D6 * em[2, 2]

    current_wrist_tilt = math.sqrt( Wx**2 + Wy**2 + validation_Wz**2 )

    if current_wrist_tilt > MAX_ROBOT_WRIST_TILT:
        return ValidErrorCode.WRIST_POSE_TOO_FAR
    
    if math.sqrt(Wx**2 + Wy**2) < 62.0 + ARM_SAFE_DISTANCE_TO_OBJECT and Wz > 0 - ARM_SAFE_DISTANCE_TO_OBJECT and Wz < 145 + ARM_SAFE_DISTANCE_TO_OBJECT: #nie można wejść do walca przy podstawie
        return ValidErrorCode.WRIST_POSE_TOO_CLOSE


    return ValidErrorCode.VALID