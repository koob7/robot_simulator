syms q0 q1 q2 q3 q4 q5 q6 D1 D4 D6 A2
syms r11 r12 r13 r21 r22 r23 r31 r32 r33

R06 = [r11, r12, r13;r21, r22, r23; r31, r32, r33]

ROBOT_DH_PARAMS = [
    0   pi/2  D1;
    A2  0     0;
    0   pi/2  0;
    0  -pi/2  D4;
    0   pi/2  0;
    0   0     D6
];

A1 = dh_transform_row(ROBOT_DH_PARAMS, 1, q0);
A2 = dh_transform_row(ROBOT_DH_PARAMS, 2, q1);
A3 = dh_transform_row(ROBOT_DH_PARAMS, 3, q2);
A4 = dh_transform_row(ROBOT_DH_PARAMS, 4, q3)
A5 = dh_transform_row(ROBOT_DH_PARAMS, 5, q4)
A6 = dh_transform_row(ROBOT_DH_PARAMS, 6, q5)

T = A1 * A2 * A3;
R03 = simplify( T(1:3, 1:3))

T = A4 * A5 * A6;
R36 = simplify( T(1:3, 1:3))


simplify(transpose(R03) * R06)
