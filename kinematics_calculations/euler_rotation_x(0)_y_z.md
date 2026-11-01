syms phi theta psi real

Ry = @(a)[ cos(a)   0   sin(a);
           0        1      0;
          -sin(a)   0   cos(a) ];

Rz = @(a)[ cos(a) -sin(a) 0;
           sin(a)  cos(a) 0;
           0       0      1 ];

Rx = @(a)[ 1 0 0;
           0 cos(a) -sin(a);
           0 sin(a)  cos(a) ];



R = Ry(phi) * Rz(theta)
R = Rx(0)*Ry(phi) * Rz(theta)
R2 =  Rz(theta) * Ry(phi);
R3 = Ry(phi) * Rz(theta) * Rx(psi);