"""SI measurements of marked bodies; no dependency on product libraries.

Door edge is the nearest lateral edge of the door body's local bounding
rectangle, including its frame. Clear area is a conservative rectangle minus
union of obstacle rectangles, not a navigation or accessibility simulation.
"""
import math
from pxr import Gf, Usd, UsdGeom
from .model import value, elements, classified, nearest, has_api

MEASURE_UNITS = {
    'measured:centreHeightAboveFloor': 'm',
    'measured:bottomHeightAboveFloor': 'm',
    'measured:distanceToDoorLeafEdge': 'm',
    'measured:sideOfDoor': '1',
    'measured:clearFloorArea': 'm2',
}


class Unmeasurable(ValueError):
    pass


class MissingBinding(Unmeasurable):
    pass


class Measurements:
    def __init__(self, stage):
        self.stage = stage
        self.scale = UsdGeom.GetStageMetersPerUnit(stage)
        self.xforms = UsdGeom.XformCache()
        self.doors = [p for p in elements(stage) if classified(p, 'ifc:IfcDoor')]
        self._points = {}
        if UsdGeom.GetStageUpAxis(stage) != 'Z':
            raise Unmeasurable('Measurements require Z-up geometry; convert the stage before checking.')

    def bodies(self, prim, role='body'):
        result = []
        for p in Usd.PrimRange(prim):
            if p != prim and has_api(p, 'AecoElementAPI'):
                continue
            if (p.IsA(UsdGeom.Gprim) and has_api(p, 'AecoDerivedGeometryAPI')
                    and value(p, 'aeco:derived:role', 'body') == role
                    and value(p, 'aeco:derived:source') == value(prim, 'aeco:id')):
                result.append(p)
        return result

    def points(self, prim, role='body'):
        key = (str(prim.GetPath()), role)
        if key in self._points:
            return self._points[key]
        result = []
        for body in self.bodies(prim, role):
            matrix = self.xforms.GetLocalToWorldTransform(body)
            if body.IsA(UsdGeom.Mesh):
                pts = UsdGeom.Mesh(body).GetPointsAttr().Get() or []
            elif body.IsA(UsdGeom.Cube):
                half = UsdGeom.Cube(body).GetSizeAttr().Get() / 2
                pts = [Gf.Vec3d(x, y, z) for x in (-half, half) for y in (-half, half) for z in (-half, half)]
            else:
                raise Unmeasurable('Only marked Mesh or Cube bounds are supported: ' + str(body.GetPath()))
            result.extend(matrix.Transform(Gf.Vec3d(p)) for p in pts)
        if not result or not all(math.isfinite(v) for p in result for v in p):
            raise Unmeasurable('No finite marked body points: ' + str(prim.GetPath()))
        self._points[key] = result
        return result

    def bounds(self, prim, role='body', frame=None):
        pts = self.points(prim, role)
        if frame is not None:
            inverse = self.xforms.GetLocalToWorldTransform(frame).GetInverse()
            pts = [inverse.Transform(p) for p in pts]
        return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))

    def centre(self, prim):
        lo, hi = self.bounds(prim)
        return Gf.Vec3d(*((lo[i] + hi[i])/2 for i in range(3)))

    def floor(self, prim):
        level = nearest(prim, {'AecoLevel'})
        if not level:
            raise Unmeasurable('No containing AecoLevel floor datum: ' + str(prim.GetPath()))
        matrix = self.xforms.GetLocalToWorldTransform(level)
        normal = matrix.TransformDir(Gf.Vec3d(0, 0, 1)).GetNormalized()
        if abs(normal[2] - 1) > 1e-6:
            raise Unmeasurable('Floor datum must be horizontal.')
        return matrix.ExtractTranslation()[2]

    def door(self, prim):
        """Resolve an exported source door reference, or a unique nearby door.

        The v0.1 search envelope is 1.5 m beyond a lateral edge and 0.75 m
        from the door plane. Multiple candidates require explicit disambiguation
        in the source model; silently choosing a nearest door hides missing data.
        """
        centre = self.centre(prim)
        level = nearest(prim, {'AecoLevel'})
        candidates = []
        source_door = value(prim, 'aeco:props:DC_Identity:Door')
        doors = self.doors
        if source_door:
            doors = [d for d in doors if value(d, 'aeco:props:DC_Identity:Id') == source_door]
            if len(doors) != 1:
                raise MissingBinding('Source door reference is absent or ambiguous.')
        for door in doors:
            if nearest(door, {'AecoLevel'}) != level:
                continue
            try:
                lo, hi = self.bounds(door, frame=door)
            except Unmeasurable:
                continue
            local = self.xforms.GetLocalToWorldTransform(door).GetInverse().Transform(centre)
            side = abs(local[1] - (lo[1] + hi[1])/2) * self.scale
            lateral = max(lo[0] - local[0], local[0] - hi[0], 0) * self.scale
            if side <= 0.75 and lateral <= 1.5:
                candidates.append((door, local, lo, hi))
        if len(candidates) != 1:
            raise MissingBinding(f'Expected one nearby door; found {len(candidates)} for {prim.GetPath()}.')
        return candidates[0]

    def clear_area(self, prim):
        space = prim if prim.GetTypeName() == 'AecoSpace' else nearest(prim, {'AecoSpace'})
        if not space:
            raise Unmeasurable('No containing space for clear floor area.')
        lo, hi = self.bounds(space, role='extent')
        # Require an axis-aligned rectangular extent, not an arbitrary room's AABB.
        vertices = self.points(space, role='extent')
        if any(not any(abs(p[i]-edge) < 1e-6 for edge in (lo[i], hi[i])) for p in vertices for i in (0, 1)):
            raise Unmeasurable('Clear area requires a rectangular space extent aligned to stage XY.')
        floor = self.floor(prim)
        rectangles = []
        for obstacle in elements(self.stage):
            if nearest(obstacle, {'AecoSpace'}) != space:
                continue
            try:
                a, b = self.bounds(obstacle)
            except Unmeasurable as exc:
                raise Unmeasurable('An obstacle has no measurable body.') from exc
            if b[2] <= floor or a[2] >= floor + 1.8/self.scale:
                continue
            rectangle = (max(a[0], lo[0]), max(a[1], lo[1]), min(b[0], hi[0]), min(b[1], hi[1]))
            if rectangle[0] < rectangle[2] and rectangle[1] < rectangle[3]:
                rectangles.append(rectangle)
        area = (hi[0]-lo[0])*(hi[1]-lo[1]) - union_area(rectangles)
        return max(0, area) * self.scale**2

    def get(self, prim, measure):
        if measure in ('measured:centreHeightAboveFloor', 'measured:bottomHeightAboveFloor'):
            lo, hi = self.bounds(prim)
            z = (lo[2]+hi[2])/2 if 'centre' in measure else lo[2]
            return (z-self.floor(prim))*self.scale
        if measure == 'measured:distanceToDoorLeafEdge':
            door, local, lo, hi = self.door(prim)
            matrix = self.xforms.GetLocalToWorldTransform(door)
            edge = min(abs(local[0]-lo[0]), abs(local[0]-hi[0]))
            return edge*matrix.TransformDir(Gf.Vec3d(1, 0, 0)).GetLength()*self.scale
        if measure == 'measured:sideOfDoor':
            door, local, lo, hi = self.door(prim)
            normal = value(door, 'aeco:props:DC_DoorApproach:ApproachNormal')
            normals = {'+X': Gf.Vec3d(1,0,0), '-X': Gf.Vec3d(-1,0,0), '+Y': Gf.Vec3d(0,1,0), '-Y': Gf.Vec3d(0,-1,0)}
            if normal not in normals:
                raise Unmeasurable('Door pull-side approach normal is not authored in core ad-hoc properties.')
            distance = Gf.Dot(self.centre(prim)-self.centre(door), normals[normal])
            if abs(distance*self.scale) < 1e-6:
                raise Unmeasurable('Reader is on the door plane; side is ambiguous.')
            return 'pull' if distance > 0 else 'push'
        if measure == 'measured:clearFloorArea':
            return self.clear_area(prim)
        if measure.startswith('measured:'):
            raise Unmeasurable('Unknown measured quantity: ' + measure)
        if measure.startswith('aeco:compliance:'):
            raise Unmeasurable('A compliance result cannot be its own measurement input.')
        result = value(prim, measure)
        if result is None or isinstance(result, bool) or not isinstance(result, (float, int, str)):
            raise Unmeasurable('Missing or nonscalar property: ' + measure)
        if isinstance(result, (int, float)) and not math.isfinite(result):
            raise Unmeasurable('Non-finite property: ' + measure)
        return result


def union_area(rectangles):
    xs = sorted({r[i] for r in rectangles for i in (0, 2)})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((r[1], r[3]) for r in rectangles if r[0] < right and r[2] > left)
        length, end = 0.0, -math.inf
        for bottom, top in intervals:
            length += max(0, top-max(bottom, end))
            end = max(end, top)
        area += (right-left)*length
    return area
