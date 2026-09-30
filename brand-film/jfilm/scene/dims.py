"""Key dimensions of the illustrative lounge (metres). Shared by the 3D
builder, the plan drawing and the camera designs; no Blender import."""
XW, XP = -6.0, 5.4          # window line, glass-partition line
Y0, YB = 0.0, 9.0           # front wall face, back wall structural face
Y_PANEL = 8.88              # reeded panel face
AXIS_X = -0.3               # lounge / niche / coffer axis
Z_CEIL, Z_COFFER, Z_SOFFIT = 3.8, 4.35, 4.6
NICHE = (-1.5, 0.9, 3.0, 9.2)       # x0, x1, top z, back y
COFFER_OPEN = (-3.8, 3.2, 2.6, 7.4)  # x0, x1, y0, y1 of ceiling opening
COFFER_WALL = (-4.0, 3.4, 2.4, 7.6)
MEET = (5.4, 9.4, 2.4, 8.4)          # meeting room x0, x1, y0, y1
MULLIONS_Y = [0.0, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0]
PARTITION_Y = [2.4, 3.6, 4.8, 6.0, 7.2, 8.4]
TABLE_C = (AXIS_X, 5.0)
SOFA = (AXIS_X, 6.30)
CHAIRS = [(-2.05, 3.85, -28.0), (1.45, 3.85, 28.0)]


