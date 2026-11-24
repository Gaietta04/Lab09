from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # Aggiungere eventuali altri attributi: Vincoli inseriti dall'utente
        self._max_giorni = None
        self._max_budget = None

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """

        # Recupero dal database tutte le relazioni tra escursioni e punti di interesse
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        # Se il DAO non ha restituito dati, interrompo il metodo
        if relazioni is None:
            return

        # Scorro tutte le relazioni recuperate
        for relazione in relazioni:
            # Recupero gli ID dal dizionario della relazione
            id_escursione = relazione["id_escursione"]
            id_punto = relazione["id_punto_interesse"]

            # Recupero gli oggetti Python dai dizionari del Model
            escursione = self.escursioni_map[id_escursione]
            punto = self.punti_interesse_map[id_punto]

            # RELAZIONE N:N - collegamento in entrambe le direzioni
            # Aggiungo il punto di interesse all'escursione
            escursione.punti_interesse.add(punto)
            # Aggiungo l'escursione al punto di interesse
            punto.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        #Lista delle escursioni disponibili nel parco selezionato
        self._escursioni_parco = []

        # Salvo i vincoli inseriti dall'utente
        # None significa che non è previsto alcun limite
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        # Seleziono soltanto le escursioni del parco scelto
        self._escursioni_parco = [
            escursione
            for escursione in self.escursioni_map.values()
            if escursione.id_parco == id_parco
        ]

        # Avvio la ricorsione con un pacchetto inizialmente vuoto
        self._ricorsione(
            start_index=0,  # Parto dalla prima escursione
            pacchetto_parziale=[],  # Nessuna escursione ancora scelta
            durata_corrente=0,  # Zero giorni utilizzati
            costo_corrente=0,  # Nessuna spesa
            valore_corrente=0,  # Gradimento iniziale pari a zero
            punti_usati=set()  # Nessun punto di interesse visitato
        )

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # è possibile cambiare i parametri formali della funzione se ritenuto opportuno

        # 🟤 A - Aggiorno la soluzione ottima
        # Controllo se il pacchetto corrente ha un voto maggiore
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        # 🟢 B - Nessun caso base esplicito necessario:
        # il ciclo termina quando non ci sono altre escursioni da provare

        # Scorro le escursioni dalla posizione start_index
        for i in range(start_index, len(self._escursioni_parco)):

            escursione = self._escursioni_parco[i]

            # 🟡 C - FILTRI: verifico tutti i vincoli
            # Controllo il limite massimo di giorni
            if self._max_giorni is not None:
                if durata_corrente + escursione.durata_giorni > self._max_giorni:
                    continue

            # Controllo il budget massimo
            if self._max_budget is not None:
                if costo_corrente + escursione.costo > self._max_budget:
                    continue

            # Controllo che non ci siano punti di interesse duplicati
            if punti_usati.intersection(escursione.punti_interesse):
                continue

            # 🔵 D - CALCOLO PARZIALE
            # Calcolo il voto totale dei punti di interesse
            # appartenenti all'escursione corrente
            valore_escursione = sum(
                punto.voto_visitatori
                for punto in escursione.punti_interesse
            )

            # Aggiungo l'escursione al pacchetto parziale
            pacchetto_parziale.append(escursione)

            # Aggiungo i suoi punti di interesse all'insieme dei punti usati
            punti_usati.update(escursione.punti_interesse)

            # 🔴 E - RICORSIONE: provo ad aggiungere altre escursioni
            self._ricorsione(
                start_index=i + 1,
                pacchetto_parziale=pacchetto_parziale,
                durata_corrente=durata_corrente + escursione.durata_giorni,
                costo_corrente=costo_corrente + escursione.costo,
                valore_corrente=valore_corrente + valore_escursione,
                punti_usati=punti_usati
            )

            # 🟣 F - BACKTRACKING: annullo la scelta corrente

            # Rimuovo l'ultima escursione
            pacchetto_parziale.pop()

            # Rimuovo i punti di interesse dell'escursione appena tolta
            punti_usati.difference_update(escursione.punti_interesse)