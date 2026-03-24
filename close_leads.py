from database import execute, fetchone
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def close_all_nuevo():
    # 1. Count
    count_row = fetchone("SELECT COUNT(*) as n FROM leads WHERE estado = 'NUEVO'")
    num = count_row['n'] if count_row else 0
    
    if num == 0:
        print("No hay leads en estado NUEVO para cerrar.")
        return

    print(f"Cerrando {num} leads en estado NUEVO...")
    
    # 2. Update
    execute(
        "UPDATE leads SET estado = 'CERRADO', resultado = 'CIERRE_ADMINISTRATIVO' WHERE estado = 'NUEVO'"
    )
    
    # 3. Audit Log
    now = datetime.now()
    execute(
        "INSERT INTO audit_logs (timestamp, actor, action, target, details) VALUES (%s, %s, %s, %s, %s)",
        (now, 'SISTEMA_ADMIN', 'MASIVE_CLOSE_QUEUE', 'LEADS_QUEUE', f"Cierre masivo de {num} leads que estaban en cola.")
    )
    
    print("¡Acción completada exitosamente!")

if __name__ == "__main__":
    close_all_nuevo()
