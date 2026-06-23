"""
Modulo per simulare e inviare log a Elasticsearch
"""
import json
import random
import time
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from typing import Dict, List


class ElkLogSimulator:
    """Classe per simulare log di servizi e inviarli a Elasticsearch"""
    
    @staticmethod
    def get_index_name(date: datetime = None) -> str:
        """
        Genera il nome dell'indice seguendo il pattern services-log-AAAA-MM
        
        Args:
            date: Data da usare (default: data corrente)
            
        Returns:
            Nome dell'indice nel formato services-log-AAAA-MM
        """
        if date is None:
            date = datetime.now()
        return f"services-log-{date.year}-{date.month:02d}"
    
    def __init__(self, host: str = "localhost", port: int = 9200, 
                 username: str = None, password: str = None, api_key: str = None):
        """
        Inizializza la connessione a Elasticsearch
        
        Args:
            host: Host di Elasticsearch
            port: Porta di Elasticsearch
            username: Username per autenticazione (opzionale)
            password: Password per autenticazione (opzionale)
            api_key: API Key per autenticazione (opzionale, alternativa a username/password)
                    Formato: "id:api_key" oppure "base64_encoded_key"
        """
        # Priorità: API Key > Username/Password > Nessuna autenticazione
        if api_key:
            self.es = Elasticsearch(
                [f"http://{host}:{port}"],
                api_key=api_key
            )
            print(f"🔑 Autenticazione tramite API Key")
        elif username and password:
            self.es = Elasticsearch(
                [f"http://{host}:{port}"],
                basic_auth=(username, password)
            )
            print(f"🔐 Autenticazione tramite Username/Password")
        else:
            self.es = Elasticsearch([f"http://{host}:{port}"])
            print(f"⚠️  Connessione senza autenticazione")
        
        # Verifica connessione
        if self.es.ping():
            print(f"✓ Connessione a Elasticsearch stabilita su {host}:{port}")
        else:
            print(f"✗ Impossibile connettersi a Elasticsearch su {host}:{port}")
    
    def _generate_service_log(self) -> Dict:
        """
        Genera un log simulato di un servizio
        
        Returns:
            Dizionario con i dati del log
        """
        services = [
            "api-gateway",
            "auth-service",
            "payment-service",
            "notification-service",
            "user-service",
            "database-service",
            "cache-service"
        ]
        
        statuses = ["OK", "KO","N.A."]
        error_messages = [
            "Connection timeout",
            "Invalid credentials",
            "Resource not found",
            "Internal server error",
            "Database connection failed",
            "Rate limit exceeded"
        ]
        
        status = random.choice(statuses)
        service = random.choice(services)
        
        
        log = {
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "service": service,
            "status": status,
            "response_time_ms": random.randint(10, 5000),
            "request_id": f"req-{random.randint(100000, 999999)}",
            "environment": random.choice(["production", "staging", "development"])
        }
        
        # Aggiungi dettagli in caso di errore
        if status == "ko":
            log["error_message"] = random.choice(error_messages)
            log["error_code"] = random.choice([400, 401, 403, 404, 500, 502, 503])
        else:
            log["http_status"] = 200
        
        return log
    
    def generate_logs(self, count: int = 10) -> List[Dict]:
        """
        Genera una lista di log simulati
        
        Args:
            count: Numero di log da generare
            
        Returns:
            Lista di dizionari contenenti i log
        """
        logs = []
        for _ in range(count):
            logs.append(self._generate_service_log())
            time.sleep(0.01)  # Piccola pausa tra i log
        
        return logs
    
    def send_log(self, log: Dict, index_name: str = None) -> bool:
        """
        Invia un singolo log a Elasticsearch
        
        Args:
            log: Dizionario contenente il log
            index_name: Nome dell'indice Elasticsearch (default: services-log-AAAA-MM)
            
        Returns:
            True se l'invio ha successo, False altrimenti
        """
        if index_name is None:
            index_name = self.get_index_name()
        try:
            response = self.es.index(index=index_name, document=log)
            print(f"✓ Log inviato: {log['service']} - {log['status']} (ID: {response['_id']})")
            return True
        except Exception as e:
            print(f"✗ Errore nell'invio del log: {e}")
            return False
    
    def send_logs_bulk(self, logs: List[Dict], index_name: str = None) -> Dict:
        """
        Invia multipli log a Elasticsearch usando bulk API
        
        Args:
            logs: Lista di dizionari contenenti i log
            index_name: Nome dell'indice Elasticsearch (default: services-log-AAAA-MM)
            
        Returns:
            Dizionario con statistiche sull'invio
        """
        if index_name is None:
            index_name = self.get_index_name()
        from elasticsearch.helpers import bulk
        
        # Prepara i documenti per bulk insert
        actions = [
            {
                "_index": index_name,
                "_source": log
            }
            for log in logs
        ]
        
        try:
            success, failed = bulk(self.es, actions, stats_only=True)
            print(f"\n✓ Bulk insert completato: {success} successi, {failed} fallimenti")
            return {"success": success, "failed": failed}
        except Exception as e:
            print(f"✗ Errore nel bulk insert: {e}")
            return {"success": 0, "failed": len(logs)}
    
    def simulate_and_send(
        self, count: int = 20, 
        index_name: str = None,
        use_bulk: bool = True):
        """
        Genera e invia log simulati a Elasticsearch
        
        Args:
            count: Numero di log da generare
            index_name: Nome dell'indice Elasticsearch (default: services-log-AAAA-MM)
            use_bulk: Se True usa bulk API, altrimenti invia uno per uno
        """
        if index_name is None:
            index_name = self.get_index_name()
        print(f"\n{'='*60}")
        print(f"Generazione di {count} log simulati...")
        print(f"{'='*60}\n")
        
        logs = self.generate_logs(count)
        
        # Stampa alcuni log di esempio
        print("\nEsempi di log generati:")
        print(json.dumps(logs[:3], indent=2, ensure_ascii=False))
        
        print(f"\n{'='*60}")
        print(f"Invio log a Elasticsearch (indice: {index_name})...")
        print(f"{'='*60}\n")
        
        if use_bulk:
            self.send_logs_bulk(logs, index_name)
        else:
            for log in logs:
                self.send_log(log, index_name)
                time.sleep(0.01)
    
    def get_log_statistics(self, index_name: str = None) -> Dict:
        """
        Recupera statistiche sui log inviati
        
        Args:
            index_name: Nome dell'indice o pattern (default: services-log-*)
            
        Returns:
            Dizionario con le statistiche
        """
        if index_name is None:
            index_name = "services-log-*"  # Pattern per tutti gli indici
        try:
            # Query per contare log ok vs ko
            query = {
                "size": 0,
                "aggs": {
                    "status_counts": {
                        "terms": {"field": "status.keyword"}
                    },
                    "service_counts": {
                        "terms": {"field": "service.keyword"}
                    }
                }
            }
            
            result = self.es.search(index=index_name, body=query)
            
            stats = {
                "total_logs": result['hits']['total']['value'],
                "status_breakdown": {},
                "service_breakdown": {}
            }
            
            for bucket in result['aggregations']['status_counts']['buckets']:
                stats['status_breakdown'][bucket['key']] = bucket['doc_count']
            
            for bucket in result['aggregations']['service_counts']['buckets']:
                stats['service_breakdown'][bucket['key']] = bucket['doc_count']
            
            return stats
        except Exception as e:
            print(f"✗ Errore nel recupero delle statistiche: {e}")
            return {}


def main():
    """Funzione principale per demo"""
    # Configurazione connessione (modifica questi parametri)
    HOST = "20.105.91.235"
    PORT = 9200
    
    # Opzione 1: Autenticazione con Username/Password
    USERNAME = None  # Imposta se necessario
    PASSWORD = None  # Imposta se necessario
    
    # Opzione 2: Autenticazione con API Key (alternativa a username/password)
    # Formato: "id:api_key" o "base64_encoded_key"
    API_KEY = None  # Es: "VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw=="
    API_KEY = "WFJINUlwd0JaSG8xX01GRm9XenE6cGo2RHN4eFJ1YUw0bXdMTHBnLUtfdw=="
    
    # Crea il simulatore (usa API_KEY se impostato, altrimenti USERNAME/PASSWORD)
    simulator = ElkLogSimulator(
        host=HOST, 
        port=PORT, 
        username=USERNAME, 
        password=PASSWORD,
        api_key=API_KEY
    )
    
    # Mostra l'indice che verrà utilizzato
    current_index = simulator.get_index_name()
    print(f"\nIndice corrente: {current_index}\n")
    
    # Genera e invia 50 log (usa automaticamente il pattern services-log-AAAA-MM)
    simulator.simulate_and_send(count=50000, use_bulk=True)
    
    # Attendi un momento per permettere l'indicizzazione
    time.sleep(2)
    
    # Mostra statistiche (cerca in tutti gli indici services-log-*)
    print(f"\n{'='*60}")
    print("Statistiche dei log inviati:")
    print(f"{'='*60}\n")
    stats = simulator.get_log_statistics()  # Usa il pattern services-log-*
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
