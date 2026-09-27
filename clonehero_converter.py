"""
Convertitore MP3 a Clone Hero MIDI
Compatibile con Python 3.14
"""

import librosa
import numpy as np
from mido import MidiFile, MidiTrack, Message, MetaMessage
from pathlib import Path
import soundfile as sf
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
import random
import contextlib
import os


class MP3ToCloneHero:
    def __init__(self, input_file):
        self.input_file = input_file
        self.output_dir = Path("converted_songs")
        self.output_dir.mkdir(exist_ok=True)
        self.tempo = 120
        self.ticks_per_beat = 480
        self.song_info = {}
        self.metadata_from_file = {}
        
    def read_mp3_metadata(self):
        """Legge i metadati dal file MP3 usando ID3"""
        try:
            # Prova con EasyID3 (più user-friendly)
            audio = EasyID3(self.input_file)
            
            # Estrai metadati disponibili
            self.metadata_from_file['name'] = audio.get('title', [''])[0] if 'title' in audio else ''
            self.metadata_from_file['artist'] = audio.get('artist', [''])[0] if 'artist' in audio else ''
            self.metadata_from_file['album'] = audio.get('album', [''])[0] if 'album' in audio else ''
            self.metadata_from_file['year'] = audio.get('date', [''])[0] if 'date' in audio else ''
            self.metadata_from_file['genre'] = audio.get('genre', [''])[0] if 'genre' in audio else ''
            
            # Filtra solo i valori non vuoti
            self.metadata_from_file = {k: v for k, v in self.metadata_from_file.items() if v}
            
            if self.metadata_from_file:
                print("\n" + "=" * 60)
                print("METADATI RILEVATI DAL FILE")
                print("=" * 60)
                for key, value in self.metadata_from_file.items():
                    print(f"  {key.capitalize()}: {value}")
                print("=" * 60)
            
            return True
        except Exception as e:
            print(f"\n⚠️  Nessun metadato trovato nel file MP3 ({str(e)})")
            return False
    
    def get_song_info(self):
        """Chiede informazioni sulla canzone all'utente, usando metadati come default"""
        print("\n" + "=" * 60)
        print("INFORMAZIONI CANZONE")
        print("=" * 60)
        
        # Titolo con default dai metadati
        default_title = self.metadata_from_file.get('name', '')
        prompt = f"Titolo della canzone"
        if default_title:
            prompt += f" [{default_title}]"
        prompt += ": "
        user_input = input(prompt).strip()
        self.song_info['name'] = user_input if user_input else default_title
        
        # Artista con default dai metadati
        default_artist = self.metadata_from_file.get('artist', '')
        prompt = f"Artista"
        if default_artist:
            prompt += f" [{default_artist}]"
        prompt += ": "
        user_input = input(prompt).strip()
        self.song_info['artist'] = user_input if user_input else default_artist
        
        # Album con default dai metadati
        default_album = self.metadata_from_file.get('album', '')
        prompt = f"Album"
        if default_album:
            prompt += f" [{default_album}]"
        prompt += " (premi Invio per saltare): "
        user_input = input(prompt).strip()
        if user_input:
            self.song_info['album'] = user_input
        elif default_album:
            self.song_info['album'] = default_album
        
        # Anno con default dai metadati
        default_year = self.metadata_from_file.get('year', '')
        prompt = f"Anno"
        if default_year:
            prompt += f" [{default_year}]"
        prompt += " (opzionale): "
        user_input = input(prompt).strip()
        if user_input:
            self.song_info['year'] = user_input
        elif default_year:
            self.song_info['year'] = default_year
        
        # Genere con default dai metadati
        default_genre = self.metadata_from_file.get('genre', '')
        prompt = f"Genere"
        if default_genre:
            prompt += f" [{default_genre}]"
        prompt += " (opzionale): "
        user_input = input(prompt).strip()
        if user_input:
            self.song_info['genre'] = user_input
        elif default_genre:
            self.song_info['genre'] = default_genre
        
        charter = input("Charter/Autore chart (opzionale): ").strip()
        if charter:
            self.song_info['charter'] = charter
        
        print("=" * 60 + "\n")
    
    def create_song_ini(self, song_folder):
        """Crea il file song.ini per Clone Hero"""
        ini_path = song_folder / "song.ini"
        
        with open(ini_path, 'w', encoding='utf-8') as f:
            f.write("[song]\n")
            f.write(f"name = {self.song_info['name']}\n")
            f.write(f"artist = {self.song_info['artist']}\n")
            
            if 'album' in self.song_info:
                f.write(f"album = {self.song_info['album']}\n")
            
            if 'year' in self.song_info:
                f.write(f"year = {self.song_info['year']}\n")
            
            if 'genre' in self.song_info:
                f.write(f"genre = {self.song_info['genre']}\n")
            
            if 'charter' in self.song_info:
                f.write(f"charter = {self.song_info['charter']}\n")
            
            # Informazioni tecniche
            f.write(f"delay = 0\n")
            f.write(f"preview_start_time = 0\n")
            
        print(f"[OK] File song.ini creato: {ini_path}")
    
    def sanitize_folder_name(self, name):
        """Rimuove caratteri non validi per nomi cartelle"""
        # Caratteri non permessi in Windows
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '')
        # Rimuovi spazi extra e limita lunghezza
        name = ' '.join(name.split())
        return name[:100]  # Max 100 caratteri
    
    def create_song_folder(self):
        """Crea la cartella per la canzone in formato Clone Hero"""
        # Nome cartella: "Artista - Titolo"
        artist = self.sanitize_folder_name(self.song_info['artist'])
        title = self.sanitize_folder_name(self.song_info['name'])
        folder_name = f"{artist} - {title}"
        
        song_folder = self.output_dir / folder_name
        song_folder.mkdir(exist_ok=True)
        
        return song_folder
    
    def load_audio(self):
        """Carica il file audio"""
        print(f"\nCaricamento {Path(self.input_file).name}...")
        # Reindirizza stderr per nascondere i messaggi mpg123 ID3
        with contextlib.redirect_stderr(open(os.devnull, 'w')):
            self.y, self.sr = librosa.load(self.input_file, sr=22050)
        print(f"[OK] Audio caricato: {len(self.y)/self.sr:.2f} secondi")
        
    def detect_tempo(self):
        """Rileva il tempo della canzone"""
        print("Rilevamento tempo...")
        tempo, beats = librosa.beat.beat_track(y=self.y, sr=self.sr)
        # Fix per NumPy 1.25+ - estrai scalare correttamente
        self.tempo = int(tempo.item() if hasattr(tempo, 'item') else tempo)
        self.beats = librosa.frames_to_time(beats, sr=self.sr)
        print(f"Tempo rilevato: {self.tempo} BPM")
        return self.tempo
    
    def separate_frequency_bands(self):
        """Separa le bande di frequenza per isolare strumenti"""
        # Usa filtri passa-banda per separare approssimativamente gli strumenti
        # Basso: 40-250 Hz
        bass = librosa.effects.percussive(self.y, margin=3.0)
        bass_filtered = self._bandpass_filter(bass, 40, 250)
        
        # Chitarra/Mid: 250-2000 Hz
        guitar = librosa.effects.harmonic(self.y, margin=3.0)
        guitar_filtered = self._bandpass_filter(guitar, 250, 2000)
        
        # Batteria: usa componente percussivo
        drums = librosa.effects.percussive(self.y, margin=2.0)
        
        return {
            'guitar': guitar_filtered,
            'bass': bass_filtered,
            'drums': drums
        }
    
    def _bandpass_filter(self, y, low_freq, high_freq):
        """Applica un filtro passa-banda"""
        # Trasforma in dominio di frequenza
        D = librosa.stft(y)
        
        # Calcola le frequenze
        freqs = librosa.fft_frequencies(sr=self.sr)
        
        # Crea maschera
        mask = (freqs >= low_freq) & (freqs <= high_freq)
        
        # Applica maschera
        D_filtered = D.copy()
        D_filtered[~mask, :] = 0
        
        # Ritorna al dominio temporale
        y_filtered = librosa.istft(D_filtered)
        
        return y_filtered
    
    def detect_guitar_notes(self, y):
        """Rileva note di chitarra usando modello personalizzato"""
        print("Analisi chitarra...")
        return self._detect_with_advanced_method(y, fmin='E2', fmax='E6', instrument='guitar')
    
    def detect_bass_notes(self, y):
        """Rileva note di basso"""
        print("Analisi basso...")
        return self._detect_with_advanced_method(y, fmin='E1', fmax='G3', instrument='bass')
    
    def _detect_with_advanced_method(self, y, fmin='E2', fmax='E6', instrument='guitar'):
        """Metodo avanzato di pitch detection combinato"""
        fmin_hz = librosa.note_to_hz(fmin)
        fmax_hz = librosa.note_to_hz(fmax)
        
        # 1. PYIN per pitch tracking (rimosso win_length deprecato)
        f0_pyin, voiced_pyin, probs_pyin = librosa.pyin(
            y,
            fmin=fmin_hz,
            fmax=fmax_hz,
            sr=self.sr,
            frame_length=2048,
            hop_length=256
        )
        
        # 2. CQT (Constant-Q Transform) per conferma
        C = np.abs(librosa.cqt(y, sr=self.sr, fmin=fmin_hz, n_bins=84, bins_per_octave=12))
        
        # 3. Onset detection per trovare inizio note
        onset_env = librosa.onset.onset_strength(y=y, sr=self.sr)
        onsets = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=self.sr,
            units='time',
            backtrack=True
        )
        
        # Combina informazioni
        notes = self._combine_pitch_and_onsets(f0_pyin, voiced_pyin, probs_pyin, onsets, C)
        
        return notes
    
    def _combine_pitch_and_onsets(self, f0, voiced, probs, onsets, cqt):
        """Combina pitch tracking e onset detection per note accurate"""
        hop_length = 256
        times = librosa.frames_to_time(np.arange(len(f0)), sr=self.sr, hop_length=hop_length)
        
        notes = []
        current_note = None
        note_start = None
        note_confidence = 0
        
        for i, (freq, is_voiced, prob) in enumerate(zip(f0, voiced, probs)):
            # Soglia di confidenza adattiva
            threshold = 0.5 if current_note is None else 0.4
            
            if is_voiced and not np.isnan(freq) and prob > threshold:
                midi_note = int(librosa.hz_to_midi(freq))
                # IMPORTANTE: Salva il MIDI_NOTE grezzo, non il fret mappato!
                # Il fret sarà mappato per ogni difficoltà in base al difficulty parameter
                
                # Verifica con CQT
                cqt_conf = self._verify_with_cqt(cqt, i, midi_note) if i < cqt.shape[1] else 0.5
                
                # Cambiamento di nota
                if current_note != midi_note:
                    # Salva nota precedente se abbastanza lunga e confidenza OK
                    if current_note is not None and note_start is not None:
                        duration = times[i] - note_start
                        if duration > 0.08 and note_confidence > 0.4:  # Min 80ms
                            # Verifica se c'è un onset vicino
                            has_onset = any(abs(note_start - o) < 0.2 for o in onsets)
                            velocity = 110 if has_onset else 90
                            
                            notes.append({
                                'time': note_start,
                                'midi_note': current_note,  # Salva MIDI nota grezzo
                                'duration': duration,
                                'velocity': velocity
                            })
                    
                    # Nuova nota
                    current_note = midi_note  # Salva il MIDI_NOTE grezzo
                    note_start = times[i]
                    note_confidence = (prob + cqt_conf) / 2
                else:
                    # Stessa nota, aggiorna confidenza
                    note_confidence = max(note_confidence, (prob + cqt_conf) / 2)
            else:
                # Fine nota
                if current_note is not None and note_start is not None:
                    duration = times[i] - note_start
                    if duration > 0.08 and note_confidence > 0.4:
                        has_onset = any(abs(note_start - o) < 0.2 for o in onsets)
                        velocity = 110 if has_onset else 90
                        
                        notes.append({
                            'time': note_start,
                            'midi_note': current_note,  # Salva MIDI nota grezzo
                            'duration': duration,
                            'velocity': velocity
                        })
                    
                    current_note = None
                    note_start = None
                    note_confidence = 0
        
        # Post-processing: rimuovi note troppo vicine
        notes = self._remove_duplicate_notes(notes, min_gap=0.05)
        
        return notes
    
    def _verify_with_cqt(self, cqt, frame_idx, midi_note):
        """Verifica la nota usando CQT"""
        if frame_idx >= cqt.shape[1]:
            return 0.5
        
        # Trova il bin CQT corrispondente alla nota MIDI
        # CQT parte da fmin, ogni ottava ha bins_per_octave bins
        cqt_bin = midi_note % 84  # 84 bins nel nostro CQT
        
        # Energia nel bin della nota
        note_energy = cqt[cqt_bin, frame_idx]
        
        # Energia totale
        total_energy = np.sum(cqt[:, frame_idx])
        
        if total_energy > 0:
            confidence = note_energy / total_energy
            return min(confidence * 2, 1.0)  # Scala a 0-1
        
        return 0.0
    
    def _remove_duplicate_notes(self, notes, min_gap=0.05):
        """Rimuove note duplicate troppo vicine"""
        if not notes:
            return []
        
        notes = sorted(notes, key=lambda x: x['time'])
        filtered = [notes[0]]
        
        for note in notes[1:]:
            prev = filtered[-1]
            time_gap = note['time'] - (prev['time'] + prev['duration'])
            
            # Usa midi_note per il confronto (non fret)
            if time_gap < min_gap and note['midi_note'] == prev['midi_note']:
                # Estendi la nota precedente
                prev['duration'] = note['time'] + note['duration'] - prev['time']
            elif note['time'] - prev['time'] > min_gap:
                filtered.append(note)
        
        return filtered
    
    def _detect_with_librosa(self, y, fmin='E2', fmax='E6'):
        """DEPRECATED - usa _detect_with_advanced_method"""
        return self._detect_with_advanced_method(y, fmin, fmax)
    
    def detect_drum_notes(self, y):
        """Rileva note batteria"""
        print("Analisi batteria...")
        
        # Onset detection avanzato
        onset_env = librosa.onset.onset_strength(
            y=y, 
            sr=self.sr,
            aggregate=np.median,
            fmax=8000,
            n_mels=256
        )
        
        onsets = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=self.sr,
            units='time',
            backtrack=True,
            delta=0.05
        )
        
        # Analizza ogni onset per classificare il tipo di drum
        drum_notes = []
        
        for onset in onsets:
            onset_sample = int(onset * self.sr)
            
            # Estrai segmento con dimensione adattiva
            segment_size = min(1024, len(y) - onset_sample)
            start = max(0, onset_sample - min(512, onset_sample))
            end = min(len(y), onset_sample + segment_size)
            segment = y[start:end]
            
            if len(segment) < 64:  # Troppo corto, salta
                continue
            
            # Usa n_fft adattivo in base alla lunghezza del segmento
            n_fft = min(2048, len(segment))
            if n_fft < 64:
                continue
            
            # Analisi spettrale
            spec = np.abs(librosa.stft(segment, n_fft=n_fft))
            freq_energy = np.sum(spec, axis=1)
            
            # Frequenze
            freqs = librosa.fft_frequencies(sr=self.sr, n_fft=n_fft)
            
            # Energia per banda
            low_mask = freqs < 150      # Kick
            mid_mask = (freqs >= 150) & (freqs < 500)   # Snare
            high_mask = (freqs >= 500) & (freqs < 3000)  # Hi-hat/Ride
            crash_mask = freqs >= 3000  # Crash
            
            low_energy = np.sum(freq_energy[low_mask])
            mid_energy = np.sum(freq_energy[mid_mask])
            high_energy = np.sum(freq_energy[high_mask])
            crash_energy = np.sum(freq_energy[crash_mask])
            
            total = low_energy + mid_energy + high_energy + crash_energy
            
            if total > 0:
                low_ratio = low_energy / total
                mid_ratio = mid_energy / total
                high_ratio = high_energy / total
                crash_ratio = crash_energy / total
                
                # Classifica
                if low_ratio > 0.5:
                    pad = 0  # Kick (verde in Clone Hero)
                elif mid_ratio > 0.4:
                    pad = 1  # Snare (rosso)
                elif crash_ratio > 0.3:
                    pad = 4  # Crash (arancione)
                elif high_ratio > 0.4:
                    pad = 2  # Hi-hat (giallo)
                else:
                    pad = 3  # Tom (blu)
            else:
                pad = 2
            
            drum_notes.append({
                'time': onset,
                'pad': pad,
                'duration': 0.1,
                'velocity': 100
            })
        
        return drum_notes
    
    def _midi_to_fret(self, midi_note, difficulty='expert'):
        """Assegna casualmente un tasto in base alla difficoltà"""
        # Tasti disponibili per difficoltà
        available_frets = {
            'easy': [0, 1, 2],              # Verde, Rosso, Giallo
            'medium': [0, 1, 2, 3],         # Verde, Rosso, Giallo, Blu
            'hard': [0, 1, 2, 3, 4],        # Tutti 5 colori
            'expert': [0, 1, 2, 3, 4]       # Tutti 5 colori
        }
        
        available = available_frets.get(difficulty, [0, 1, 2, 3, 4])
        
        # Assegna casualmente un tasto tra quelli disponibili
        fret = random.choice(available)
        
        return fret
        return fret
    
    def combine_all_instruments(self, guitar_notes, bass_notes, drum_notes):
        """Combina tutte le note da tutti gli strumenti in una singola lista"""
        combined = []
        
        # Aggiungi note chitarra
        for note in guitar_notes:
            combined.append({
                'time': note['time'],
                'midi_note': note.get('midi_note', note.get('fret', 60)),  # Può avere sia midi_note che fret
                'duration': note['duration'],
                'velocity': note.get('velocity', 100),
                'source': 'guitar'
            })
        
        # Aggiungi note basso
        for note in bass_notes:
            combined.append({
                'time': note['time'],
                'midi_note': note.get('midi_note', note.get('fret', 40)),  # Può avere sia midi_note che fret
                'duration': note['duration'],
                'velocity': note.get('velocity', 100),
                'source': 'bass'
            })
        
        # Aggiungi note batteria (converti pad a fret)
        for note in drum_notes:
            combined.append({
                'time': note['time'],
                'pad': note['pad'],  # Mantieni pad per batteria, non midi_note
                'duration': note['duration'],
                'velocity': note.get('velocity', 100),
                'source': 'drums'
            })
        
        # Ordina per tempo
        combined = sorted(combined, key=lambda x: x['time'])
        return combined
    
    def create_difficulty_variations(self, notes, difficulty, is_drums=False):
        """Crea variazioni di difficoltà con percentuali specifiche e tasti limitati"""
        if not notes:
            return []
        
        # Ordina per tempo
        notes = sorted(notes, key=lambda x: x['time'])
        
        # Filtra note per difficoltà (percentuale-based)
        filtered_notes = []
        
        if difficulty == 'easy':
            # 25% note
            filtered_notes = [n for i, n in enumerate(notes) if i % 4 == 0]
        elif difficulty == 'medium':
            # 50% note
            filtered_notes = [n for i, n in enumerate(notes) if i % 2 == 0]
        elif difficulty == 'hard':
            # 75% note
            filtered_notes = [n for i, n in enumerate(notes) if i % 4 != 3]
        else:  # expert
            # 100% note
            filtered_notes = notes
        
        return filtered_notes
    
    def create_midi_track(self, notes, track_name, difficulty, is_drums=False):
        """Crea traccia MIDI Clone Hero"""
        track = MidiTrack()
        track.append(MetaMessage('track_name', name=track_name))
        
        # Offset note MIDI per difficoltà Clone Hero
        difficulty_offset = {
            'easy': 60,
            'medium': 72,
            'hard': 84,
            'expert': 96
        }
        
        base_note = difficulty_offset[difficulty]
        last_time = 0
        
        for note in notes:
            # Converti tempo in ticks MIDI
            time_ticks = int(note['time'] * self.ticks_per_beat * (self.tempo / 60))
            duration_ticks = max(int(note['duration'] * self.ticks_per_beat * (self.tempo / 60)), 10)
            
            delta_time = max(0, time_ticks - last_time)
            
            if is_drums:
                note_num = base_note + note['pad']
            else:
                # Mappa il MIDI_NOTE a fret in base alla difficoltà scelta
                midi_note = note.get('midi_note', note.get('fret', 60))
                fret = self._midi_to_fret(midi_note, difficulty=difficulty)
                note_num = base_note + fret
            
            velocity = note.get('velocity', 100)
            
            track.append(Message('note_on', note=note_num, velocity=velocity, time=delta_time))
            track.append(Message('note_off', note=note_num, velocity=0, time=duration_ticks))
            
            last_time = time_ticks + duration_ticks
        
        return track
    
    def create_clone_hero_midi(self, guitar_notes, bass_notes, drum_notes):
        """Crea file MIDI Clone Hero con traccia GUITAR LEAD combinata"""
        midi = MidiFile(ticks_per_beat=self.ticks_per_beat)
        
        # Traccia eventi globali
        tempo_track = MidiTrack()
        tempo_track.append(MetaMessage('set_tempo', tempo=int(60000000 / self.tempo)))
        tempo_track.append(MetaMessage('time_signature', numerator=4, denominator=4))
        midi.tracks.append(tempo_track)
        
        difficulties = ['easy', 'medium', 'hard', 'expert']
        
        # Combina tutti gli strumenti
        print("Combinazione di tutti gli strumenti...")
        combined_notes = self.combine_all_instruments(guitar_notes, bass_notes, drum_notes)
        
        # Tracce GUITAR LEAD combinate
        print("Creazione tracce GUITAR LEAD (combinata)...")
        for diff in difficulties:
            diff_notes = self.create_difficulty_variations(combined_notes, diff, is_drums=False)
            
            # Le note hanno già midi_note, create_midi_track mapperà per difficoltà
            if diff_notes:
                track = self.create_midi_track(diff_notes, 'PART GUITAR', diff)
                midi.tracks.append(track)
            else:
                # Aggiungi traccia vuota per consistenza
                track = MidiTrack()
                track.append(MetaMessage('track_name', name='PART GUITAR'))
                midi.tracks.append(track)
        
        return midi
    
    def convert(self):
        """Processo completo di conversione"""
        print("=" * 60)
        print("CONVERTITORE MP3 -> CLONE HERO MIDI")
        print("=" * 60)
        
        # 0a. Leggi metadati dal file MP3
        self.read_mp3_metadata()
        
        # 0b. Chiedi informazioni sulla canzone
        self.get_song_info()
        
        # 1. Carica audio
        self.load_audio()
        
        # 2. Rileva tempo
        self.detect_tempo()
        
        # 3. Separa frequenze
        stems = self.separate_frequency_bands()
        
        # 4. Rileva note per ogni strumento
        guitar_notes = self.detect_guitar_notes(stems['guitar'])
        print(f"  -> {len(guitar_notes)} note chitarra rilevate")
        
        bass_notes = self.detect_bass_notes(stems['bass'])
        print(f"  -> {len(bass_notes)} note basso rilevate")
        
        drum_notes = self.detect_drum_notes(stems['drums'])
        print(f"  -> {len(drum_notes)} note batteria rilevate")
        
        total_combined = len(guitar_notes) + len(bass_notes) + len(drum_notes)
        print(f"  -> {total_combined} note totali da combinare")
        
        # 5. Crea cartella canzone
        print("\nCreazione struttura cartelle Clone Hero...")
        song_folder = self.create_song_folder()
        
        # 6. Crea MIDI
        print("Creazione file MIDI Clone Hero...")
        midi = self.create_clone_hero_midi(guitar_notes, bass_notes, drum_notes)
        
        # 7. Salva MIDI nella cartella canzone
        song_name = Path(self.input_file).stem
        midi_file = song_folder / "notes.mid"
        midi.save(str(midi_file))
        print(f"[OK] File MIDI salvato: {midi_file}")
        
        # 8. Copia/converte file audio nella cartella (da MP3 a OGG se necessario)
        self._copy_audio_file(song_folder)
        
        # 9. Crea song.ini
        self.create_song_ini(song_folder)
        
        print("=" * 60)
        print("[OK] CONVERSIONE COMPLETATA!")
        print(f"[OK] Cartella canzone: {song_folder}")
        print(f"[OK] Tempo: {self.tempo} BPM")
        print(f"[OK] Traccia: GUITAR LEAD (combinata da tutti gli strumenti)")
        print(f"[OK] Difficoltá: Easy, Medium, Hard, Expert")
        print(f"[OK] Note combinate: {total_combined}")
        print("\n[NOTE] ISTRUZIONI:")
        print(f"1. Copia la cartella '{song_folder.name}'")
        print("2. Incollala nella cartella 'songs' di Clone Hero")
        print("3. Riavvia Clone Hero")
        print("=" * 60)
        
        return song_folder
    
    def _copy_audio_file(self, song_folder):
        """Copia il file audio nella cartella della canzone"""
        input_path = Path(self.input_file)
        
        # Copia come OGG se Clone Hero preferisce, altrimenti come MP3
        output_audio = song_folder / "song.ogg"
        alt_output = song_folder / "song.mp3"
        
        # Prova prima OGG
        try:
            print(f"Conversione audio a OGG...")
            # Se è MP3, copia per ora (conversione può richiedere ffmpeg)
            if input_path.suffix.lower() == '.mp3':
                # Fallback: copia direttamente come MP3
                import shutil
                shutil.copy2(str(input_path), str(alt_output))
                print(f"[OK] File audio copiato: {alt_output}")
            else:
                import shutil
                shutil.copy2(str(input_path), str(output_audio))
                print(f"[OK] File audio copiato: {output_audio}")
        except Exception as e:
            print(f"[WARNING] Avviso: impossibile copiare file audio ({e})")
            print("   Clone Hero potrebbe non riprodurre la preview")


# Utilizzo
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = input("\nInserisci il percorso di un file MP3 o una cartella: ").strip()
    
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"\n[ERROR] Errore: '{input_path}' non trovato")
        sys.exit(1)
    
    # Lista di file da processare
    mp3_files = []
    
    if input_path.is_file():
        # E' un singolo file
        if input_path.suffix.lower() == '.mp3':
            mp3_files = [input_path]
        else:
            print(f"\n[ERROR] Errore: il file deve essere un MP3")
            sys.exit(1)
    elif input_path.is_dir():
        # E' una cartella - trova tutti i .mp3
        mp3_files = sorted(input_path.glob("*.mp3"))
        if not mp3_files:
            print(f"\n[ERROR] Errore: nessun file MP3 trovato in '{input_path}'")
            sys.exit(1)
        print(f"\n[INFO] Trovati {len(mp3_files)} file MP3 da convertire\n")
    else:
        print(f"\n[ERROR] Errore: '{input_path}' non è un file o una cartella valida")
        sys.exit(1)
    
    # Processa ogni file
    for mp3_file in mp3_files:
        try:
            print(f"[PROCESSING] Elaborazione: {mp3_file.name}")
            converter = MP3ToCloneHero(str(mp3_file))
            converter.convert()
            
            # Elimina il file MP3 dopo la conversione riuscita
            mp3_file.unlink()
            print(f"[OK] File eliminato: {mp3_file.name}\n")
            
        except Exception as e:
            print(f"[ERROR] Errore durante l'elaborazione di {mp3_file.name}: {e}\n")
            continue
    
    print("[OK] Conversione batch completata!")
