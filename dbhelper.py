try:
    # pypyodbc is only required for optional remote DB features and is
    # Windows / ODBC specific. On macOS / non-Windows we skip importing it
    # so the local SQLite-backed editor can still run.
    import pypyodbc as pyodbc  # type: ignore
except Exception:
    pyodbc = None

import sqlite3
from sqlite3 import Error
import json
import traceback
import sys 
import datetime
import re

LDBFN = "db/sqllite.db"

code_create_sql = """
create table if not exists code (
    codeid integer primary key AUTOINCREMENT,
    codename text not null,
    folderid integer not null,
    codevalue text not null,
    codetype text nont null,
    version integer not null default 1,
    state text not null default 'draft',
    locked_by text,
    locked_at text,
    FOREIGN KEY(folderid) REFERENCES folder(folderid)    
);
"""

folder_create_sql = """
create table if not exists folder (
    folderid integer primary key AUTOINCREMENT,
    foldername text not null,
    folderparent integer,
    FOREIGN KEY(folderparent) REFERENCES folder(folderid)
)
"""


codehistory_create_sql = """
create table if not exists codehistory (
    historyid integer primary key AUTOINCREMENT,
    codeid integer not null,
    codevalue text not null,
    changedate text not null,
    version integer not null default 1,
    changed_by text,
    state text,
    FOREIGN KEY(codeid) REFERENCES code(codeid)
)
"""

remote_create_sql = """
create table if not exists remote (
    remoteid integer primary key AUTOINCREMENT,
    remotename text not null,
    remotecs text not null
)
"""

aisettings_create_sql = """
create table if not exists aisettings (
    settingid integer primary key AUTOINCREMENT,
    provider text not null,
    apikey text not null,
    model text not null,
    isactive integer not null default 0
)
"""

# Migration SQL to add new columns to existing tables
code_migration_sql = [
    "ALTER TABLE code ADD COLUMN version integer not null default 1",
    "ALTER TABLE code ADD COLUMN state text not null default 'draft'",
    "ALTER TABLE code ADD COLUMN locked_by text",
    "ALTER TABLE code ADD COLUMN locked_at text"
]

codehistory_migration_sql = [
    "ALTER TABLE codehistory ADD COLUMN version integer not null default 1",
    "ALTER TABLE codehistory ADD COLUMN changed_by text",
    "ALTER TABLE codehistory ADD COLUMN state text"
]

folder_init_sql = """
insert into folder (foldername)
select 'Local' 
WHERE NOT EXISTS(select 1 from folder where foldername = 'Local' and folderparent is null)
"""

code_init_sql = """
insert into code (codename,folderid,codevalue,codetype)
select 'Test',1,'This is a test','html'
WHERE NOT EXISTS(select 1 from code where codename = 'Test' and folderid = 1)
"""

class dbhelper(object):
    def __init__(self):
        self.lcreate()

    def lconn(self):
        return sqlite3.connect(LDBFN)

    def lcreate(self):
        conn = None
        try:
            conn = self.lconn()
            c = conn.cursor()
            c.execute(folder_create_sql)
            c.execute(code_create_sql)
            c.execute(codehistory_create_sql)
            c.execute(folder_init_sql)
            c.execute(code_init_sql)
            c.execute(remote_create_sql)
            c.execute(aisettings_create_sql)
            
            # Run migrations for existing databases
            for migration in code_migration_sql:
                try:
                    c.execute(migration)
                except:
                    pass  # Column already exists
            
            for migration in codehistory_migration_sql:
                try:
                    c.execute(migration)
                except:
                    pass  # Column already exists
            
            conn.commit()
        except Error as e:
            traceback.print_exc(file=sys.stdout)
            print (e)
        finally:
            if conn: conn.close()

    def GetTreePath(self,path):
        if path == None:
            #get the root object
            conn = self.lconn()
            c = conn.cursor()
            sf = "select folderid,foldername,folderparent from folder"# where folderparent is null order by foldername"
            c.execute(sf)
            folderrows = c.fetchall()
            s = "SELECT codeid,codename,folderid,codetype from code"# where folderid in (select folderid from folder where folderparent is null)"
            c.execute(s)
            coderows = c.fetchall()
            if conn: conn.close()
            ret = { 'Nodes': [] }
            f2 = list(filter(lambda x: not x[2],folderrows))
            for f in f2:
                ctn = {
                    'CodeId': 'l' + str(f[0]),
                    'CodeName': f[1],
                    'CodeInsertBy': 'System',
                    'CodeInsertDate': '2014-12-04 10:36:00',
                    'CodeIsScope': True,
                    'CodeIsSystem': True,
                    'CodeType': None,
                    'Nodes': self.recursivenode(f[2],folderrows,coderows),
                    'CodeRevision': None
                    }
                ret['Nodes'].append(ctn)

            rtn = {
                'CodeId': 'r',
                'CodeName': 'Remote',
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': True,
                'CodeIsSystem': True,
                'CodeType': None,
                'Nodes': self.populateremote(),
                'CodeRevision': None
                }
            ret['Nodes'].append(rtn)

            return json.dumps(ret)
        else:
            #get a submodule
            return ''

    

    def recursivenode(self,folderid,folders,codes):
        f2 = list(filter(lambda x: x[2] == folderid ,folders))
        c2 = list(filter(lambda x: x[2] == folderid,codes))
        if len(f2) == 0 and len(c2) == 0: return []
        ret = []
        for f in f2:
            ctn = {
            'CodeId': 'l' + str(f[0]),
            'CodeName': f[1],
            'CodeInsertBy': 'System', #Used only in history
            'CodeInsertDate': '2014-12-04 10:36:00', #used only in history
            'CodeIsScope': True,
            'CodeIsSystem': True,
            'CodeType': None, 
            'Nodes': [],
            'CodeRevision': None
            }            
            ctn['Nodes'] = self.recursivenode(f[0],folders,codes)
            ret.append(ctn)
        for c in c2:
            ctn2 = {
            'CodeId': 'l' + str(c[0]),
            'CodeName': c[1],
            'CodeInsertBy': 'System', #used only in history
            'CodeInsertDate': '2014-12-04 10:36:00', #used only in history
            'CodeIsScope': False,
            'CodeIsSystem': True,
            'CodeType': c[3], #/ace/mode codetype
            'Nodes': [],
            'CodeRevision': None #added to name if set
            }
            ret.append(ctn2)
        return ret

    def GetCode(self,codeid):
        if not codeid: return ''
        codeid = str(codeid)
        if codeid.startswith('r'): 
            pass
        if codeid.startswith('l'): codeid = codeid[1:]
        conn = self.lconn()
        c = conn.cursor()
        sf = "select codeid,codename,folderid,codetype,codevalue,version,state,locked_by,locked_at from code where codeid = ?"
        c.execute(sf,[codeid])
        row = c.fetchone()
        if not row: return '{ "Text": "Failed to locate code ' + str(codeid) + ' " }'
        #returns, Text: <error message>, relogin=1 redirect to login, 
        ret = {
            'CodeId': row[0],
            'CodeName': row[1],
            'CodeInsertBy': 'System',
            'CodeInsertDate': '2019-01-01',
            'CodeIsSystem': True,
            'CodeType': row[3],
            'CodeValue': row[4],
            'CodeRevision': None,
            'Version': row[5] if len(row) > 5 else 1,
            'State': row[6] if len(row) > 6 else 'draft',
            'LockedBy': row[7] if len(row) > 7 else None,
            'LockedAt': row[8] if len(row) > 8 else None
        }
        if conn: conn.close()
        return json.dumps(ret)

    def GetCodeRaw(self,codeid):        
        if not codeid: return ''
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        conn = self.lconn()
        c = conn.cursor()
        sf = "select codevalue from code where codeid = ?"
        c.execute(sf,[codeid])
        row = c.fetchone()
        if not row: raise ModuleNotFoundError
        code = row[0]
        if conn: conn.close()
        return code

    def SaveCode(self,codeid,code,user='system'):
        if not codeid or not code: return ''
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        conn = self.lconn()
        c = conn.cursor()
        
        # Check if code is locked by someone else
        c.execute("SELECT locked_by, locked_at FROM code WHERE codeid = ?", [codeid])
        lock_info = c.fetchone()
        if lock_info and lock_info[0] and lock_info[0] != user:
            if conn: conn.close()
            return f'FAILED: Code is locked by {lock_info[0]} since {lock_info[1]}'
        
        dt = datetime.datetime.now().isoformat()
        
        # Archive current version with version number and state
        archive = """
        INSERT INTO codehistory (codeid, codevalue, changedate, version, changed_by, state) 
        SELECT codeid, codevalue, ?, version, ?, state 
        FROM code WHERE codeid = ?
        """
        c.execute(archive, [dt, user, codeid])
        if not c.rowcount: 
            if conn: conn.close()
            return 'FAILED to insert codehistory'
        
        # Update code and increment version
        up = """
        UPDATE code 
        SET codevalue = ?, version = version + 1 
        WHERE codeid = ?
        """
        c.execute(up, [code, codeid])
        if not c.rowcount: 
            if conn: conn.close()
            return 'FAILED to update code'
        
        conn.commit()
        if conn: conn.close()
        return 'SUCCESS'

    def RenameCode(self,codeid,codename):
        if not codeid or not codename: return ''
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        conn = self.lconn()
        c = conn.cursor()
        s = "UPDATE code set codename = ? where codeid = ?"
        c.execute(s,[codename,codeid])
        if not c.rowcount: return 'FAILED to rename code'
        conn.commit()
        if conn: conn.close()
        return 'SUCCESS'

    def NewScope(self,parentfolderid,scopename,issystem):
        #TODO handle issystem
        if not parentfolderid or not scopename or not issystem: return ''
        parentfolderid = str(parentfolderid)
        if parentfolderid.startswith('l'): parentfolderid = parentfolderid[1:]
        if parentfolderid == '-1': parentfolderid = None
        conn = self.lconn()
        c = conn.cursor()
        s = "INSERT INTO folder (foldername,folderparent) VALUES (?,?)"
        c.execute(s,[scopename,parentfolderid])
        if not c.rowcount: return 'FAILED to create scope'
        conn.commit()
        if conn: conn.close()
        return 'SUCCESS'

    def NewCode(self,parentfolderid,codename,issystem,codetype,isversioned):
        if not parentfolderid or not codename or not issystem or not codetype or not isversioned: return ''
        parentfolderid = str(parentfolderid)
        if parentfolderid.startswith('l'): parentfolderid = parentfolderid[1:]
        if parentfolderid == '-1': parentfolderid = None
        conn = self.lconn()
        c = conn.cursor()
        s = "INSERT INTO code (codename,folderid,codevalue,codetype) VALUES (?,?,?,?) "
        c.execute(s,[codename,parentfolderid,'',codetype])
        if not c.rowcount: return 'FAILED to insert code'
        lastrowid = c.lastrowid
        dt = datetime.datetime.now().isoformat()
        s = "INSERT INTO codehistory (codeid,codevalue,changedate) VALUES (?,?,?)"
        c.execute(s,[lastrowid,'',dt])
        if not c.rowcount: return 'FAILED to insert codehistory NewCode'
        conn.commit()
        if conn: conn.close()
        return 'SUCCESS'

    def MoveCode(self,codeID,newScopeID):
        if not codeID or not newScopeID: return ''
        codeID = str(codeID)
        newScopeID = str(newScopeID)
        if codeID.startswith('l'): codeID = codeID[1:]
        if newScopeID.startswith('l'): newScopeID = newScopeID[1:]
        conn = self.lconn()
        c = conn.cursor()
        s = "UPDATE code SET folderid = ? WHERE codeid = ?"
        c.execute(s,[newScopeID,codeID])
        if not c.rowcount: return 'FAILED to update code'
        conn.commit()
        if conn: conn.close()
        return 'SUCCESS'

    def CodeHistory(self,codeid):
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        #determine how to handle current or insert a dummy record into history
        ret = []
        conn = self.lconn()
        c = conn.cursor()
        s2 = "SELECT codeid,codename,codetype FROM code WHERE codeid = ?"
        c.execute(s2,[codeid])
        tcode = c.fetchone()
        if not c.rowcount: return 'FAILED to locate code ' + str(codeid)
        s = "SELECT historyid,codeid,codevalue,changedate FROM codehistory where codeid = ?"
        c.execute(s,[codeid])
        if not c.rowcount: return 'FAILED to locate codehistory codeid = '  + str(codeid) 
        rows = c.fetchall()
        for r in rows:
            ce = {
                'CodeId': r[0],
                'CodeName': tcode[1],
                'CodeInsertBy': 'System',
                'CodeInsertDate': r[3],
                'CodeIsSystem': True,
                'CodeType': tcode[2],
                'CodeValue': r[2],
                'CodeRevision': None
                }
            ret.append(ce)
        if conn: conn.close()
        return json.dumps(ret)

    ##################################### Remote DB Code ##############################################
    def populateremote(self):
        # If pypyodbc is unavailable (e.g. on macOS), skip remote DB population.
        if pyodbc is None:
            return []

        conn = self.lconn()
        c = conn.cursor()
        s = "SELECT remoteid, remotename, remotecs from remote"
        c.execute(s)
        remoterows = c.fetchall()
        ret = []
        for r in remoterows:
            rtn = {
                'CodeId': 'r' + str(r[0]),
                'CodeName': r[1],
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': True,
                'CodeIsSystem': True,
                'CodeType': None,
                'Nodes': self.getremotenodes(r[2],r[0]),
                'CodeRevision': None
                }
            ret.append(rtn)
        return ret

    def getremotenodes(self,remotecs,remoteid):
        ret = []
        db = pyodbc.connect(remotecs)
        s = "set nocount on; exec CodeTreeGetTree"
        cursor = db.cursor()
        cursor.execute(s)
        rows = cursor.fetchall()

        #Below is a hack to flatten our internal system
        if '10.12.2.71' in remotecs:
            system = next(x for x in rows if x[1] == 3)
            apps = next(x for x in rows if x[1] == 84)
            rtnsys = {
                'CodeId': 'r' + str(system[1]),
                'CodeName': str(system[2]),
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': system[5],
                'CodeIsSystem': system[6],
                'CodeType': None,
                'Nodes': self.remoterecursive(rows,system,remoteid),
                'CodeRevision': None
                }
            ret.append(rtnsys)
            rtnapp = {
                'CodeId': 'r' + str(apps[1]),
                'CodeName': str(apps[2]),
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': apps[5],
                'CodeIsSystem': apps[6],
                'CodeType': None,
                'Nodes': self.remoterecursive(rows,apps,remoteid),
                'CodeRevision': None
                }
            ret.append(rtnapp)

        else:
            frow = rows[0] 
            rtn = {
                'CodeId': 'r' + str(frow[1]),
                'CodeName': str(frow[2]),
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': frow[5],
                'CodeIsSystem': frow[6],
                'CodeType': None,
                'Nodes': self.remoterecursive(rows,frow,remoteid),
                'CodeRevision': None
                }
            ret.append(rtn)
        cursor.close()
        db.close()
        return ret

    ##################################### Version Locking & State Machine ##############################################
    
    def LockCode(self, codeid, user='system'):
        """Lock a code file for editing"""
        if not codeid or not user: 
            return json.dumps({'status': 'FAILED', 'message': 'Missing codeid or user'})
        
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        
        conn = self.lconn()
        c = conn.cursor()
        
        # Check if already locked
        c.execute("SELECT locked_by, locked_at FROM code WHERE codeid = ?", [codeid])
        lock_info = c.fetchone()
        
        if lock_info and lock_info[0]:
            if lock_info[0] == user:
                if conn: conn.close()
                return json.dumps({'status': 'SUCCESS', 'message': 'Already locked by you'})
            else:
                if conn: conn.close()
                return json.dumps({
                    'status': 'FAILED', 
                    'message': f'Code is locked by {lock_info[0]} since {lock_info[1]}'
                })
        
        # Lock the code
        dt = datetime.datetime.now().isoformat()
        c.execute("UPDATE code SET locked_by = ?, locked_at = ? WHERE codeid = ?", [user, dt, codeid])
        conn.commit()
        if conn: conn.close()
        
        return json.dumps({'status': 'SUCCESS', 'message': f'Locked by {user}'})
    
    def UnlockCode(self, codeid, user='system'):
        """Unlock a code file"""
        if not codeid: 
            return json.dumps({'status': 'FAILED', 'message': 'Missing codeid'})
        
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        
        conn = self.lconn()
        c = conn.cursor()
        
        # Check if locked by this user
        c.execute("SELECT locked_by FROM code WHERE codeid = ?", [codeid])
        lock_info = c.fetchone()
        
        if lock_info and lock_info[0] and lock_info[0] != user:
            if conn: conn.close()
            return json.dumps({
                'status': 'FAILED', 
                'message': f'Cannot unlock - locked by {lock_info[0]}'
            })
        
        # Unlock the code
        c.execute("UPDATE code SET locked_by = NULL, locked_at = NULL WHERE codeid = ?", [codeid])
        conn.commit()
        if conn: conn.close()
        
        return json.dumps({'status': 'SUCCESS', 'message': 'Unlocked'})
    
    def GetLockStatus(self, codeid):
        """Get lock status of a code file"""
        if not codeid: 
            return json.dumps({'status': 'FAILED', 'message': 'Missing codeid'})
        
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        
        conn = self.lconn()
        c = conn.cursor()
        c.execute("SELECT locked_by, locked_at FROM code WHERE codeid = ?", [codeid])
        lock_info = c.fetchone()
        if conn: conn.close()
        
        if lock_info and lock_info[0]:
            return json.dumps({
                'status': 'LOCKED',
                'locked_by': lock_info[0],
                'locked_at': lock_info[1]
            })
        else:
            return json.dumps({'status': 'UNLOCKED'})
    
    def ChangeCodeState(self, codeid, new_state, user='system'):
        """Change the state of a code file (draft, locked, published, archived)"""
        valid_states = ['draft', 'locked', 'published', 'archived']
        
        if new_state not in valid_states:
            return json.dumps({
                'status': 'FAILED', 
                'message': f'Invalid state. Must be one of: {", ".join(valid_states)}'
            })
        
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        
        conn = self.lconn()
        c = conn.cursor()
        
        # Get current state
        c.execute("SELECT state FROM code WHERE codeid = ?", [codeid])
        current = c.fetchone()
        
        if not current:
            if conn: conn.close()
            return json.dumps({'status': 'FAILED', 'message': 'Code not found'})
        
        old_state = current[0]
        
        # Update state
        c.execute("UPDATE code SET state = ? WHERE codeid = ?", [new_state, codeid])
        conn.commit()
        if conn: conn.close()
        
        return json.dumps({
            'status': 'SUCCESS',
            'old_state': old_state,
            'new_state': new_state,
            'changed_by': user
        })
    
    def GetCodeState(self, codeid):
        """Get the current state of a code file"""
        if not codeid: 
            return json.dumps({'status': 'FAILED', 'message': 'Missing codeid'})
        
        codeid = str(codeid)
        if codeid.startswith('l'): codeid = codeid[1:]
        
        conn = self.lconn()
        c = conn.cursor()
        c.execute("SELECT state, version FROM code WHERE codeid = ?", [codeid])
        info = c.fetchone()
        if conn: conn.close()
        
        if info:
            return json.dumps({
                'status': 'SUCCESS',
                'state': info[0],
                'version': info[1]
            })
        else:
            return json.dumps({'status': 'FAILED', 'message': 'Code not found'})

    ##################################### AI Settings Code ##############################################
    def SaveAISettings(self, provider, apikey, model):
        if not provider or not apikey or not model: 
            return json.dumps({'status': 'FAILED', 'message': 'Missing required fields'})
        conn = self.lconn()
        c = conn.cursor()
        # Deactivate all existing settings
        c.execute("UPDATE aisettings SET isactive = 0")
        # Insert new setting as active
        s = "INSERT INTO aisettings (provider, apikey, model, isactive) VALUES (?, ?, ?, 1)"
        c.execute(s, [provider, apikey, model])
        if not c.rowcount: 
            if conn: conn.close()
            return json.dumps({'status': 'FAILED', 'message': 'Failed to save AI settings'})
        conn.commit()
        if conn: conn.close()
        return json.dumps({'status': 'SUCCESS'})

    def GetActiveAISettings(self):
        conn = self.lconn()
        c = conn.cursor()
        s = "SELECT provider, apikey, model FROM aisettings WHERE isactive = 1 ORDER BY settingid DESC LIMIT 1"
        c.execute(s)
        row = c.fetchone()
        if conn: conn.close()
        if not row:
            return json.dumps({'status': 'NONE'})
        return json.dumps({
            'status': 'SUCCESS',
            'provider': row[0],
            'apikey': row[1],
            'model': row[2]
        })

    def GetAllAISettings(self):
        conn = self.lconn()
        c = conn.cursor()
        s = "SELECT settingid, provider, apikey, model, isactive FROM aisettings ORDER BY settingid DESC"
        c.execute(s)
        rows = c.fetchall()
        if conn: conn.close()
        settings = []
        for r in rows:
            settings.append({
                'id': r[0],
                'provider': r[1],
                'apikey': r[2][:10] + '...' if len(r[2]) > 10 else r[2],  # Mask API key
                'model': r[3],
                'isactive': r[4]
            })
        return json.dumps(settings)

    def remoterecursive(self,rows,thisrow,remoteid):
        ret = []
        treestr = thisrow[0]
        regex = '^'+treestr+ r"[\d]+/$"
        desendant = list(filter(lambda x: re.match(regex,x[0]),rows))
        for r in desendant:
            rtn = {
                'CodeId': 'r' + str(r[1]),
                'CodeName': str(r[2]),
                'CodeInsertBy': 'System',
                'CodeInsertDate': '2014-12-04 10:36:00',
                'CodeIsScope': r[5],
                'CodeIsSystem': r[6],
                'CodeType': None,
                'Nodes': self.remoterecursive(rows,r,remoteid), #[], #self.remoterecursive(rows,frow),
                'CodeRevision': None
                }
            ret.append(rtn)
        return ret
