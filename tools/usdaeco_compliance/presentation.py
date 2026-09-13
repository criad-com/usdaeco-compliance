"""Author reproducible USD drawing sheets from measured bodies and verdicts.

These are publication figures, separate from the building and the check inputs.
Every figure prim is marked so freshness hashing ignores presentation changes.
"""
from pathlib import Path
from PIL import ImageFont
from pxr import Sdf, Usd, UsdGeom, Gf
from .measure import Measurements
from .model import value, elements, classified, requirements, specifications, nearest, attr
from .study import study_root, define_scopes, record_root, selected_specification

INK=(.065,.10,.16)
GREY=(.72,.77,.81)
GREEN=(.08,.55,.34)
RED=(.87,.16,.18)
BLUE=(.17,.44,.76)
AMBER=(.84,.52,.10)
PAPER=(.96,.97,.98)


class Sheet:
    def __init__(self, stage, root, source):
        self.stage,self.root,self.n=stage,root,0
        self.source=source
        stage.DefinePrim(root,'Scope')

    def mesh(self, rectangles, colour, z=.01):
        if not rectangles:return
        self.n+=1
        mesh=UsdGeom.Mesh.Define(self.stage,f'{self.root}/Shape{self.n:04d}')
        points=[]
        for x,y,w,h in rectangles:
            points.extend([(x,y,z),(x+w,y,z),(x+w,y+h,z),(x,y+h,z)])
        mesh.CreatePointsAttr(points)
        mesh.CreateFaceVertexCountsAttr([4]*len(rectangles))
        mesh.CreateFaceVertexIndicesAttr(list(range(len(points))))
        mesh.CreateSubdivisionSchemeAttr('none')
        mesh.CreateDoubleSidedAttr(True)
        mesh.CreateDisplayColorAttr([colour])
        prim=mesh.GetPrim()
        prim.AddAppliedSchema('AecoDerivedGeometryAPI')
        attr(prim,'aeco:derived:source',Sdf.ValueTypeNames.String,self.source)
        attr(prim,'aeco:derived:role',Sdf.ValueTypeNames.Token,'symbol')
        attr(prim,'aeco:derived:approx',Sdf.ValueTypeNames.Token,'bbox')
        attr(prim,'aeco:derived:stamp',Sdf.ValueTypeNames.String,'aeco-compliance 0.1.0 publication')
        return mesh

    def rect(self,x,y,w,h,c,z=.01): return self.mesh([(x,y,w,h)],c,z)

    def outline(self,x,y,w,h,c,width=.02,z=.02):
        self.mesh([(x,y,w,width),(x,y+h-width,w,width),(x,y,width,h),(x+w-width,y,width,h)],c,z)

    def text(self,x,y,text,height=.20,colour=INK):
        font=ImageFont.load_default(size=18)
        mask=font.getmask(text,mode='1'); width,pixels_high=mask.size
        if not width or not pixels_high:return
        scale=height/pixels_high
        pixels=list(mask);rectangles=[]
        for row in range(pixels_high):
            start=None
            for col in range(width+1):
                on=col<width and pixels[row*width+col]>0
                if on and start is None:start=col
                elif not on and start is not None:
                    rectangles.append((x+start*scale,y+(pixels_high-1-row)*scale,(col-start)*scale,scale))
                    start=None
        self.mesh(rectangles,colour,.08)


def draw(stage, result, output):
    measurements=Measurements(stage)
    layer=Sdf.Layer.CreateNew(str(Path(output).resolve()))
    layer.customLayerData={'aecoComplianceRole':'presentation','illustrative':True}
    figures=Usd.Stage.Open(layer)
    bad=next(r for r in result['results'] if r['status']=='fail')
    reader=stage.GetPrimAtPath(bad['path'])
    facility=nearest(reader,{'AecoFacility'})
    if not facility:raise ValueError('Publication figures need the containing facility referent.')
    figure_root=str(facility.GetPath().AppendChild('ComplianceFigures'))
    location=study_root(stage)
    if location == Sdf.Path.absoluteRootPath:
        figures.OverridePrim(facility.GetPath())
    else:
        define_scopes(figures,location)
        figure_root=str(location.AppendChild('ComplianceFigures'))
        record_root(layer,location)
    transform=UsdGeom.Xform.Define(figures,figure_root)
    transform.SetResetXformStack(True)
    transform.AddTranslateOp().Set((0,0,20))
    source=value(facility,'aeco:id')
    elevation=Sheet(figures,figure_root+'/Elevation',source)
    plan=Sheet(figures,figure_root+'/Plan',source)
    door,_,lo,hi=measurements.door(reader)
    floor=measurements.floor(reader)
    # Draw the door elevation from actual door bounds in its local XZ frame.
    centre=measurements.xforms.GetLocalToWorldTransform(door).GetInverse().Transform(measurements.centre(reader))
    door_lo,door_hi=measurements.bounds(door,frame=door)
    body_lo,body_hi=measurements.bounds(reader)
    scale=2.0; ox,oy=1.15,1.2
    elevation.rect(-1,-1,18,12,PAPER,0)
    elevation.text(.55,9.35,'IRIS READER / DOOR ELEVATION',.36)
    elevation.text(.55,8.80,'demo-datacentre-01  |  office-link door  |  ILLUSTRATIVE',.21)
    elevation.rect(.55,8.48,14.9,.025,INK)
    elevation.rect(.8,oy-.045,6.0,.04,INK)
    elevation.outline(ox,oy,(door_hi[0]-door_lo[0])*scale,(door_hi[2]-door_lo[2])*scale,INK,.035)
    rx=ox+(centre[0]-door_lo[0])*scale
    rz=oy+(measurements.centre(reader)[2]-floor)*scale
    elevation.rect(rx-.10,rz-.16,.20,.32,RED,.06)
    elevation.text(rx+.2,rz+.20,'FAIL  1.65 m',.23,RED)
    elevation.text(.8,.62,'Floor datum / 0.00 m',.19)
    columns=[('accessibility',BLUE,7.1),('employer_security',GREEN,8.5),('reader_datasheet',AMBER,9.9)]
    for name,colour,x in columns:
        spec=selected_specification(stage,bad,name)
        req=next(r for r in requirements(spec) if value(r,'aeco:req:measure')=='measured:centreHeightAboveFloor')
        a,b=value(req,'aeco:req:values')
        elevation.rect(x,oy+a*scale,.60,(b-a)*scale,colour,.02)
        elevation.text(x-.1,oy+b*scale+.15,f'{b:g} m',.18,colour)
        elevation.text(x-.1,oy+a*scale-.35,f'{a:g} m',.18,colour)
    elevation.rect(rx,rz,10.75-rx,.016,RED,.035)
    elevation.text(11,rz-.08,'Measured centre',.18,RED)
    for y,text,c in [(7.7,'Accessibility: 0.90-1.20 m  /  FAIL',BLUE),
                     (7.22,'Employer security: 1.05-1.20 m  /  FAIL',GREEN),
                     (6.74,'Reader datasheet: 1.00-1.70 m  /  PASS',AMBER)]:
        elevation.rect(.65,y,.14,.18,c)
        elevation.text(.92,y,text,.21,c)
    elevation.text(6.9,.62,'Three source bands; values are illustrative.',.18)
    elevation.text(.65,.20,'Two failed clauses, one failed device. Door outline includes the frame.',.17)
    # Plan sheet uses actual XY body projections on the ground level.
    plan.rect(29,-1,18,12,PAPER,0)
    plan.text(30.55,9.35,'IRIS READERS / GROUND PLAN',.36)
    counts={s:sum(r['status']==s for r in result['results']) for s in ('pass','fail')}
    plan.text(30.55,8.80,f"{len(result['results'])} readers  |  {counts['pass']} PASS  |  {counts['fail']} FAIL  |  ILLUSTRATIVE",.23)
    plan.rect(30.55,8.48,14.9,.025,INK)
    factor=.175; offset=(31.1,1.55)
    for prim in elements(stage):
        if not (classified(prim,'ifc:IfcWall') or classified(prim,'ifc:IfcDoor')):continue
        try:a,b=measurements.bounds(prim)
        except ValueError:continue
        if a[2]>.1:continue
        x=offset[0]+a[0]*factor;y=offset[1]+a[1]*factor
        right=x+max((b[0]-a[0])*factor,.015)
        top=y+max((b[1]-a[1])*factor,.015)
        x,y=max(x,30.8),max(y,1.55)
        right,top=min(right,45.2),min(top,8.2)
        if right>x and top>y:plan.rect(x,y,right-x,top-y,GREY,.01)
    for i,row in enumerate(result['results'],1):
        prim=stage.GetPrimAtPath(row['path']);p=measurements.centre(prim)
        x=offset[0]+p[0]*factor;y=offset[1]+p[1]*factor
        colour=GREEN if row['status']=='pass' else RED
        plan.rect(x-.085,y-.085,.17,.17,colour,.04)
        plan.text(x+.13,y+.03,str(i),.15,colour)
    plan.rect(30.65,.72,.14,.16,GREEN);plan.text(30.92,.72,f"{counts['pass']} readers within all active clauses",.20)
    plan.rect(38.0,.72,.14,.16,RED);plan.text(38.27,.72,'Office-link: 1.65 m',.20,RED)
    plan.text(30.65,.20,'Markers enlarged for legibility. Main building shown; office wing clipped below the link door.',.16)
    for prim in Usd.PrimRange(figures.GetPrimAtPath(figure_root)):
        prim.SetCustomDataByKey('aecoCompliancePresentation',True)
    layer.Save()
    stage.GetRootLayer().subLayerPaths.insert(0,str(Path(output).resolve()))
    return layer


def present_facility(stage, result, output):
    """Colour original reader bodies and draw illustrative height envelopes.

    The overview camera clips above the ground-floor readers. All source prims,
    bodies and transforms remain composed; only display opinions are authored.
    Symbols sit under each reader, share its identity and never enter measurement.
    """
    measurements = Measurements(stage)
    layer = Sdf.Layer.CreateNew(str(Path(output).resolve()))
    layer.customLayerData = {'aecoComplianceRole': 'presentation', 'illustrative': True}
    view = Usd.Stage.Open(layer)
    for row in result['results']:
        reader = stage.GetPrimAtPath(row['path'])
        colour = GREEN if row['status'] == 'pass' else RED
        for body in measurements.bodies(reader):
            prim = view.OverridePrim(body.GetPath())
            display = UsdGeom.Gprim(prim).CreateDisplayColorAttr([colour])
            display.SetMetadata('aecoDerived', True)
        root = str(reader.GetPath().AppendChild('ComplianceEnvelope'))
        xform = UsdGeom.Xform.Define(view, root)
        xform.SetResetXformStack(True)
        centre = measurements.centre(reader)
        floor = measurements.floor(reader)
        source = value(reader, 'aeco:id')

        def lines(name, paths, colour, width):
            # Mesh bars also render in stock CPU delegates without curve support.
            mesh = UsdGeom.Mesh.Define(view, root + '/' + name)
            points, indices = [], []
            faces = [(0,1,3,2), (4,6,7,5), (0,4,5,1),
                     (2,3,7,6), (0,2,6,4), (1,5,7,3)]
            for path in paths:
                for a, b in zip(path, path[1:]):
                    low = [min(a[i], b[i])-width/2 for i in range(3)]
                    high = [max(a[i], b[i])+width/2 for i in range(3)]
                    start = len(points)
                    points.extend((x,y,z) for x in (low[0], high[0])
                                  for y in (low[1], high[1]) for z in (low[2], high[2]))
                    indices.extend(start+i for face in faces for i in face)
            mesh.CreatePointsAttr(points)
            mesh.CreateFaceVertexCountsAttr([4]*(len(indices)//4))
            mesh.CreateFaceVertexIndicesAttr(indices)
            mesh.CreateSubdivisionSchemeAttr('none')
            mesh.CreateDoubleSidedAttr(True)
            mesh.CreateDisplayColorAttr([colour])
            prim = mesh.GetPrim()
            prim.AddAppliedSchema('AecoDerivedGeometryAPI')
            attr(prim, 'aeco:derived:source', Sdf.ValueTypeNames.String, source)
            attr(prim, 'aeco:derived:role', Sdf.ValueTypeNames.Token, 'symbol')
            attr(prim, 'aeco:derived:approx', Sdf.ValueTypeNames.Token, 'bbox')
            attr(prim, 'aeco:derived:stamp', Sdf.ValueTypeNames.String,
                 'aeco-compliance illustrative height envelope')
            for prop in prim.GetAuthoredProperties():
                prop.SetMetadata('aecoDerived', True)

        # Concentric boxes expose all three clause bands in the facility itself.
        for name, colour_band, radius in [('accessibility', BLUE, .50),
                                          ('employer_security', GREEN, .38),
                                          ('reader_datasheet', AMBER, .26)]:
            spec = selected_specification(stage, row, name)
            req = next(r for r in requirements(spec)
                       if value(r, 'aeco:req:measure') == 'measured:centreHeightAboveFloor')
            low, high = value(req, 'aeco:req:values')
            rings = [[(centre[0]+dx, centre[1]+dy, floor+height)
                      for dx, dy in [(-radius,-radius), (radius,-radius),
                                     (radius,radius), (-radius,radius), (-radius,-radius)]]
                     for height in (low, high)]
            lines(name, rings + [[rings[0][i], rings[1][i]] for i in range(4)],
                  colour_band, .025)
        # An enlarged status cross identifies the actual body centre in a full plan.
        x, y, z = centre
        lines('Status', [[(x-.18,y,z), (x+.18,y,z)],
                         [(x,y-.18,z), (x,y+.18,z)],
                         [(x,y,z-.18), (x,y,z+.18)]], colour, .09)
        for prim in Usd.PrimRange(xform.GetPrim()):
            prim.SetCustomDataByKey('aecoCompliancePresentation', True)
    layer.Save()
    stage.GetRootLayer().subLayerPaths.insert(0, str(Path(output).resolve()))
    return layer
