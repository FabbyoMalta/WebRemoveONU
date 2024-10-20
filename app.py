from flask import Flask, render_template, request, redirect, url_for, flash
import telnetlib
import time
import os

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')  # Substitua por uma chave secreta real

# Configurações da OLT (use variáveis de ambiente)
OLT_HOST = os.environ.get('OLT_HOST') or "10.1.10.14"
OLT_USERNAME = os.environ.get('OLT_USERNAME').encode('utf-8') or b"seu_usuario"
OLT_PASSWORD = os.environ.get('OLT_PASSWORD').encode('utf-8') or b"sua_senha"

class ONU:
    def __init__(self, fsp_value=None, ont_id=None, status=None, description=None, frame_slot=None, pon=None):
        self.fsp_value = fsp_value
        self.ont_id = ont_id
        self.status = status
        self.description = description
        self.frame_slot = frame_slot
        self.pon = pon

def connect_to_olt(host, username, password):
    try:
        tn = telnetlib.Telnet(host)
        tn.read_until(b"name:")
        tn.write(username + b"\n")
        tn.read_until(b"password:")
        tn.write(password + b"\n")
        tn.write(b"enable\n")
        tn.write(b"config\n")
        return tn
    except Exception as e:
        print(f"Erro ao conectar à OLT: {str(e)}")
        return None

def execute_command(tn, command):
    try:
        tn.write(command + b"\n")
        return tn.read_until(b") ----", timeout=10)
    except Exception as e:
        print(f"Erro ao executar o comando: {str(e)}")
        return None

def onu_exists(output):
    if output is not None:
        return b"The required ONT does not exist" not in output, output
    else:
        return False, None

def process_output(output):
    onu = ONU()
    if output is not None:
        onu.fsp_value = get_fsp_value(output)
        onu.ont_id = get_ont_id(output)
        onu.status = get_status(output)
        onu.description = get_description(output)
        onu.frame_slot = get_frame_slot(onu.fsp_value)
        onu.pon = get_pon(onu.fsp_value)
    return onu

def get_fsp_value(output):
    lines = output.splitlines()
    for line in lines:
        if b"F/S/P" in line:
            return line.split(b":")[1].strip().decode('utf-8') if line else None
    return None

def get_frame_slot(fsp_value):
    return fsp_value[:3]

def get_pon(fsp_value):
    if len(fsp_value) == 5:
        return fsp_value[-1:]
    elif len(fsp_value) == 6:
        return fsp_value[-2:]
    return None

def get_ont_id(output):
    lines = output.splitlines()
    for line in lines:
        if b"ONT-ID" in line:
            return line.split(b":")[1].strip().decode('utf-8') if line else None
    return None

def get_status(output):
    lines = output.splitlines()
    for line in lines:
        if b"Run state" in line:
            return line.split(b":")[1].strip().decode('utf-8') if line else None
    return None

def get_description(output):
    lines = output.splitlines()
    for line in lines:
        if b"Description" in line:
            return line.split(b":")[1].strip().decode('utf-8') if line else None
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        sn = request.form['sn']
        if len(sn) >= 4:
            onu = query_onu(sn)
            if onu and onu.fsp_value:
                return render_template('result.html', onu=onu)
            else:
                flash('A ONU não está cadastrada na OLT.')
                return redirect(url_for('index'))
        else:
            flash('Por favor, informe pelo menos 4 caracteres do SN.')
            return redirect(url_for('index'))
    return render_template('index.html')

def query_onu(sn):
    tn = connect_to_olt(OLT_HOST, OLT_USERNAME, OLT_PASSWORD)
    if tn:
        command_result = execute_command(tn, b"display ont info by-sn " + sn.encode('utf-8'))
        if command_result:
            onu_exists_result, output = onu_exists(command_result)
            if onu_exists_result:
                onu = process_output(output)
                tn.close()
                return onu
        tn.close()
    return None

@app.route('/delete_onu', methods=['POST'])
def delete_onu():
    fsp_value = request.form['fsp_value']
    ont_id = request.form['ont_id']
    frame_slot = request.form['frame_slot']
    pon = request.form['pon']

    onu = ONU(fsp_value=fsp_value, ont_id=ont_id, frame_slot=frame_slot, pon=pon)

    tn = connect_to_olt(OLT_HOST, OLT_USERNAME, OLT_PASSWORD)
    if tn:
        success = delete_onu_command(tn, onu)
        tn.close()
        if success:
            flash('SUCESSO! ONU excluída.', 'success')  # Mensagem de sucesso
        else:
            flash('Exclusão não funcionou. Procure um analista.', 'danger')  # Mensagem de erro
    else:
        flash('Conexão não foi estabelecida. Verifique as credenciais e o host.', 'danger')
    return redirect(url_for('index'))

def delete_onu_command(tn, onu):
    try:
        command0 = b"q\n"
        command1 = b"undo service-port port " + onu.fsp_value.encode('utf-8') + b" ont " + onu.ont_id.encode('utf-8') + b"\n"
        command2 = b"y\n"
        command3 = b"interface gpon " + onu.frame_slot.encode('utf-8') + b"\n"
        command4 = b"ont delete " + onu.pon.encode('utf-8') + b" " + onu.ont_id.encode('utf-8') + b"\n"

        commands = [command0, command1, command2, command3, command4]
        for cmd in commands:
            tn.write(cmd)
            time.sleep(0.5)

        output = tn.read_very_eager()
        if b"Number of ONTs that can be deleted: 1, success: 1" in output:
            return True
        else:
            return False
    except Exception as e:
        print(f"Erro ao excluir a ONU: {str(e)}")
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0')
