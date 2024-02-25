import os
import glob
from datetime import datetime
import json

from flask import Flask, render_template, request, Response, send_from_directory

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='hfdjioewvbr98436b7t98v4b3vt84b3t8cnbq85e71vbu98c7qpv',
        BASE_DIR='.'
    )

    if test_config is not None:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    basedir = os.path.abspath(app.config['BASE_DIR'])
    renderdir = os.path.join(basedir, 'renders')
    os.makedirs(renderdir, exist_ok=True)

    jobs = []

    def find_job(job_id):
        for job in jobs:
            if job['id'] == job_id:
                return job
        raise KeyError("No such job")
    
    def write_job(job):
        projectdir = os.path.join(renderdir, job['id'])
        os.makedirs(projectdir, exist_ok=True)
        filename = os.path.join(projectdir, 'job.json')
        with open(filename, 'w') as f:
            json.dump(job, f)

    @app.get('/app')
    def get_app():
        return render_template('app.html')

    @app.route('/api/config')
    def get_config():
        return {
            'basedir': basedir
        }

    # PROJECTS
    @app.route('/projects')
    def get_projects():
        return [ os.path.basename(x)[:-6] for x in glob.glob(os.path.join(basedir, "*.blend")) ]
    
    @app.route('/projects/<path:project>')
    def get_project(project):
       return send_from_directory(basedir, f'{project}.blend')

    # JOBS
    @app.route('/jobs')
    def get_queued():
        return jobs
    
    @app.put("/jobs")
    def add_job():
        try:
            data = request.get_json()
            project = data['project']
            start_frame = int(data['start'])
            end_frame = int(data['end'])
            priority = int(data.get('priority', 0))
        except:
            return Response("Malformed input", 400)

        job = {
            'id': datetime.now().isoformat(timespec='microseconds'),
            'project': project,
            'start': start_frame,
            'end': end_frame, 
            'priority': priority,
            'queued': list(range(start_frame, end_frame+1)),
            'total': end_frame - start_frame + 1,
            'status': 'accepted',
            'assigned': {},
            'complete': {},
        }
        write_job(job)

        jobs.append(job)
        jobs.sort(key=lambda x: (x['priority'], x['id']))
        return Response('Job created', 201)

    @app.delete("/jobs/<jobid>")
    def delete_job(jobid):
        try:
            job = find_job(jobid)
            jobs.remove(job)
            return Response('Job deleted', 204)
        except KeyError:
            return Response('No such job', 404)

    # RENDERS
    @app.get("/renders")
    def get_renders():
        result = os.listdir(renderdir)
        result.sort(reverse=True)
        return result

    @app.get('/renders/<jobid>/images')
    def job_file_list(jobid):
        try:
            job = find_job(jobid)
        except KeyError:
            return Response('No such job', 404)
        return glob.glob(os.path.join(renderdir, job['id']), "*.png")

    @app.get("/renders/<jobid>/<path:filename>")
    def download_render(jobid, filename):
        folder = os.path.join(renderdir, jobid) 
        return send_from_directory(folder, filename)

    @app.put("/renders/<jobid>/<path:filename>")
    def upload_result(jobid, filename):
        try:
            job = find_job(jobid)
        except KeyError:
            return Response('No such job', 404)
        upload_dir = os.path.join(renderdir, job['id'])
        fn = os.path.join(upload_dir, filename)
        with open(fn, 'wb') as f:
            f.write(request.data)
        return Response('File uploaded', 201)
        

    # TASKS    
    @app.get('/tasks/request')
    def request_task():
        frames = int(request.args.get('frames', 1))

        for job in jobs:
            if len(job['queued']) == 0:
                continue
            
            job['status'] = 'processing'
            task = {
                'job_id': job['id'],
                'project': job['project'],
                'frames': job['queued'][:frames],
                'worker': request.remote_addr,
                'time': datetime.now().isoformat(timespec="seconds")
            }
            task_id = f"{task['frames'][0]}_{task['frames'][-1]}"
            task['task_id'] = task_id
            job['queued'] = job['queued'][frames:]
            job['assigned'][task_id] = task
            return task
        
        return Response('No jobs available', 404)

    @app.put('/tasks/complete')
    def task_completed():
        data = request.get_json()
        job = find_job(data['job_id'])
        task = job['assigned'].pop(data['task_id'])

        started = datetime.fromisoformat(task['time'])
        task['duration'] = (datetime.now() - started).seconds
        task['status'] = 'complete'

        job['complete'][task['task_id']] = task

        if not job['queued'] and not job['assigned']:
            job['status'] = "complete"
            write_job(job)
            jobs.remove(job)

        return Response('Task marked complete', 201)

    @app.put('/tasks/failed')
    def task_failed():
        data = request.get_json()
        job = find_job(data['job_id'])
        task = job['assigned'].pop(data['task_id'])
        
        # TODO: store failed tasks?
        
        job['queued'].extend(task['frames'])
        return Response('Task requeued', 201)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run()