#!/usr/bin/env python

# Copyright (C) 2010 Arnaud Renevier <arno@renevier.net>

import os, sys, shutil, psycopg2, glob
from mako.template import Template

def createRiver(cursor, index, osm_id, name, sandre, parent=None):
    print (("computing river %s - osm_id %s") % (name,osm_id))
    river = River(osm_id, name, sandre=sandre, parent=parent)
    index[osm_id] = river
    sql = "SELECT r.osm_id, r.name, r.sandre FROM relations INNER JOIN tributaries ON relations.osm_id = tributaries.main_id INNER JOIN relations r ON tributaries.tributary_id = r.osm_id WHERE relations.osm_id = %s ORDER BY tributaries.id"  % osm_id;
    cursor.execute(sql, (osm_id,))
    for (ch_osm_id, ch_name, ch_sandre) in cursor.fetchall():
        if index.has_key(ch_osm_id):
            sys.stderr.write("trying to insert an already present river: #%s\n" % (ch_osm_id))
            continue
        tributary = createRiver(cursor, index, ch_osm_id, ch_name, ch_sandre, river)
        river.childs.append(tributary)

    #sql = "WITH RECURSIVE t(geom) AS(SELECT (ST_Dump(geom)).geom AS geom FROM relations WHERE osm_id = %s UNION ALL SELECT ST_Union(f.geom, t.geom) FROM (SELECT (st_dump(geom)).geom AS geom FROM relations WHERE osm_id = %s) AS f, t  WHERE ST_StartPoint(f.geom) = ST_EndPoint(t.geom)) SELECT max(ST_Length(ST_LineMerge(geom), TRUE)) FROM t" % (osm_id,  osm_id);
    sql = "SELECT (sum(ST_Length_Spheroid(geom,'SPHEROID[\"WGS 84\",6378137,298.257223563]'))/1000) FROM relations WHERE osm_id = %s"  % osm_id;
    cursor.execute(sql, (osm_id,osm_id))
    river.length = float(cursor.fetchone()[0] or 0)
   
    sql = "SELECT r1.osm_id, r1.name FROM relations r1 INNER JOIN relations r2 ON (ST_Intersects(r1.geom, r2.geom) AND r1.t = 'boundary') INNER JOIN (SELECT ST_DumpPoints(geom) AS geom FROM relations WHERE osm_id = %s) r3 ON ST_Intersects((r3.geom).geom, ST_MakePolygon(r1.geom)) WHERE r2.osm_id = %s ORDER BY (r3.geom).path" % (osm_id, osm_id)
    cursor.execute(sql, (osm_id,))
    seens = {}
    for (ci_osm_id, ci_name) in cursor.fetchall():
        if seens.has_key(ci_osm_id):
            continue
        river.cities.append((ci_osm_id, unicode(ci_name, 'utf-8')))
        seens[ci_osm_id] = True;

    sql = "SELECT w.osm_id, w.name FROM waysinrel INNER JOIN ways ON waysinrel.way_id = ways.osm_id INNER JOIN ways w ON ST_LineCrossingDirection(ways.geom, w.geom) != 0 WHERE w.t = 'bridge' AND waysinrel.rel_id = %s ORDER BY waysinrel.id, ST_Distance(w.geom, ST_StartPoint(ways.geom))" % osm_id
    cursor.execute(sql, (osm_id,))
    for (br_osm_id, br_name) in cursor.fetchall():
        river.bridges.append((br_osm_id, unicode(br_name, 'utf-8')))
        
    sql = "SELECT osm_id, name FROM waysinrel INNER JOIN ways ON waysinrel.way_id = ways.osm_id WHERE t = 'lock' AND waysinrel.rel_id = %s ORDER BY waysinrel.id, ST_Distance(geom, ST_StartPoint(ways.geom));" % osm_id
    cursor.execute(sql, (osm_id,))
    for (lo_osm_id, lo_name) in cursor.fetchall():
        river.locks.append((lo_osm_id, unicode(lo_name, 'utf-8')))
     
    sql = "SELECT osm_id, name FROM waysinrel INNER JOIN ways ON waysinrel.way_id = ways.osm_id WHERE t = 'tunnel' AND waysinrel.rel_id = %s ORDER BY waysinrel.id, ST_Distance(geom, ST_StartPoint(ways.geom));" % osm_id
    cursor.execute(sql, (osm_id,))
    for (lo_osm_id, lo_name) in cursor.fetchall():
        river.tunnels.append((lo_osm_id, unicode(lo_name, 'utf-8')))

    return river

class River(object):
    def __init__(self, osm_id, name, sandre = None, childs=None, cities=None, bridges=None, locks=None,  tunnels=None, length=0, parent=None):
        self.osm_id = osm_id
        self.name = unicode(name, 'utf-8')
        self.length = length
        if sandre != None:
            self.sandre = unicode(sandre, 'utf-8')
        else:
            self.sandre = ""
        self.parent = parent
        if childs:
            self.childs = childs
        else:
            self.childs = []
        if cities:
            self.cities = cities
        else:
            self.cities = []
        if bridges:
            self.bridges = bridges
        else:
            self.bridges = []
        if locks:
            self.locks = locks
        else:
            self.locks = []
        if tunnels:
            self.tunnels = tunnels
        else:
            self.tunnels = []

def outputriver(river):
    template = Template(filename='templates/river.html', input_encoding="utf-8", output_encoding="utf-8", strict_undefined=True)
    with open("htmloutput/%d.html" % (river.osm_id), "w") as fd:
        print "output for river #%d - name %s - sandre %s" % (river.osm_id, river.name, river.sandre)
        fd.write(template.render(river=river))
    for tributary in river.childs:
        outputriver(tributary)

if __name__ == '__main__':
    indextemplate = Template(filename='templates/index.html', input_encoding="utf-8", output_encoding="utf-8", strict_undefined=True)

    conn = psycopg2.connect("dbname='osm' user='osm' host='localhost' password='osm'")
    cursor = conn.cursor()

    cursor.execute("SELECT osm_id, name, sandre FROM roots ORDER BY name")

    index = {}
    roots = []
    for (osm_id, name, sandre) in cursor.fetchall():
        if index.has_key(osm_id):
            sys.stderr.write("trying to insert an already present river: #%s\n" % (osm_id))
            continue
        river = createRiver(cursor, index, osm_id, name, sandre)
        roots.append(river) 
    roots.sort(key=lambda r: r.length, reverse=True)

    shutil.rmtree("htmloutput", True);
    os.mkdir("htmloutput")
    for fname in (glob.glob("templates/*.js") + glob.glob("templates/*.png")):
        shutil.copy(fname, "htmloutput")

    with open("htmloutput/index.html", "w") as fd:
        print "generating main index"
        fd.write(indextemplate.render(roots=roots))

    for river in roots:
        outputriver(river)

    conn.close()
