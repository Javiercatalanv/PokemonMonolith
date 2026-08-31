import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface TypeRead {
  id: number;
  name: string;
}

export interface PokemonRead {
  id: number;
  name: string;
  type1: TypeRead;
  type2: TypeRead | null;
  hp: number;
  attack: number;
  defense: number;
  sp_attack: number;
  sp_defense: number;
  speed: number;
  stat_total: number;
  sprite_url?: string | null;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface GenerationRead {
  number: number;
  name: string;
  region: string;
  first_id: number;
  last_id: number;
  total_species: number;
  loaded: number;
}

export interface MatchupRead {
  attacker_type: string;
  defender: string;
  multiplier: number;
  label: string;
}

export interface TopPokemonRead {
  name: string;
  score: number;
}

export interface CounterPickRead {
  enemy: PokemonRead;
  counter: PokemonRead;
  advantage: number;
  offense_multiplier: number;
  incoming_multiplier: number;
  label: string;
}

export interface CounterTeamRead {
  total_advantage: number;
  picks: CounterPickRead[];
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="header">
      <div class="container header-content">
        <div>
          <h1>Pokemon Monolith - Generador de Counter Team</h1>
          <p class="subtitle">Interfaz Angular para analisis de tipos y generacion de equipos counter</p>
        </div>
        <div class="api-config">
          <label for="api-url">Base API URL:</label>
          <input type="text" id="api-url" [(ngModel)]="apiUrl" />
          <button (click)="checkHealth()" class="btn btn-secondary">Comprobar Estado</button>
        </div>
      </div>
    </header>

    <main class="container main-layout">
      <!-- Barra de Estado del Backend -->
      <section class="card status-bar">
        <div class="status-item">
          <span class="status-label">Liveness (API):</span>
          <span [class]="livenessClass()">{{ livenessStatus() }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Readiness (BD):</span>
          <span [class]="readinessClass()">{{ readinessStatus() }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">Total en BD:</span>
          <span [class]="totalLoadedClass()">{{ totalLoaded() }} registros</span>
        </div>
      </section>

      <!-- Pestanas Principales -->
      <nav class="nav-tabs">
        <button
          class="tab-btn"
          [class.active]="activeTab() === 'counter'"
          (click)="activeTab.set('counter')"
        >
          Generador de Counter Team
        </button>
        <button
          class="tab-btn"
          [class.active]="activeTab() === 'catalog'"
          (click)="activeTab.set('catalog')"
        >
          Catalogo y Analisis Individual
        </button>
      </nav>

      <!-- VISTA 1: GENERADOR DE EQUIPO COUNTER -->
      @if (activeTab() === 'counter') {
        <section class="card">
          <div class="card-header">
            <h2>Constructor de Equipo Rival (1 a 6 Pokemon)</h2>
            <p class="card-description">
              Ingresa los Pokemon de tu equipo o del rival. El backend analizara la matriz de tipos de 18x18
              y generara el equipo optimo que maximice la ventaja neta.
            </p>
          </div>

          <!-- Selector rapido para agregar al equipo -->
          <div class="team-builder-controls">
            <div class="form-group" style="max-width: 320px;">
              <label for="quick-add-pokemon">Buscar Pokemon por Nombre o ID:</label>
              <input
                type="text"
                id="quick-add-pokemon"
                [(ngModel)]="quickAddInput"
                placeholder="Ej: charizard, 1, squirtle..."
                (keydown.enter)="addQuickPokemon()"
              />
            </div>
            <div class="form-group btn-group-align">
              <button (click)="addQuickPokemon()" [disabled]="myTeam().length >= 6" class="btn btn-primary">
                Agregar al Equipo
              </button>
              <button (click)="loadRandomTeam()" [disabled]="pokemonList().length === 0" class="btn btn-secondary">
                Equipo de Ejemplo
              </button>
            </div>
          </div>

          @if (teamError()) {
            <div class="alert alert-danger">{{ teamError() }}</div>
          }

          <!-- Grid de Slots del Equipo -->
          <div class="team-grid">
            @for (slot of [0, 1, 2, 3, 4, 5]; track slot) {
              @if (myTeam()[slot]; as p) {
                <div class="team-slot filled">
                  <div class="flex-between" style="width: 100%;">
                    <span class="team-slot-number">Slot {{ slot + 1 }}</span>
                    <button (click)="removePokemonFromTeam(slot)" class="btn btn-sm btn-danger" title="Quitar">
                      X
                    </button>
                  </div>
                  @if (p.sprite_url) {
                    <img [src]="p.sprite_url" [alt]="p.name" class="pokemon-slot-img" />
                  }
                  <div>
                    <div class="team-member-name">#{{ p.id }} {{ capitalize(p.name) }}</div>
                    <div>
                      <span class="type-badge" [class]="'type-' + p.type1.name.toLowerCase()">
                        {{ capitalize(p.type1.name) }}
                      </span>
                      @if (p.type2) {
                        <span class="type-badge" [class]="'type-' + p.type2.name.toLowerCase()">
                          {{ capitalize(p.type2.name) }}
                        </span>
                      }
                    </div>
                  </div>
                  <div class="text-muted" style="font-size: 0.75rem;">
                    Stats: <strong>{{ p.stat_total }}</strong>
                  </div>
                </div>
              } @else {
                <div class="team-slot">
                  <span class="team-slot-number">Slot {{ slot + 1 }}</span>
                  <p class="team-slot-empty">Vacio</p>
                </div>
              }
            }
          </div>

          <!-- Barra de Acciones del Equipo -->
          <div class="team-actions-bar">
            <div>
              <label class="checkbox-label">
                <input type="checkbox" [(ngModel)]="excludeMyTeam" />
                Excluir a los miembros de este equipo como candidatos counter
              </label>
            </div>
            <div style="display: flex; gap: 0.5rem;">
              <button (click)="clearTeam()" [disabled]="myTeam().length === 0" class="btn btn-secondary">
                Limpiar Equipo
              </button>
              <button
                (click)="generateCounterTeam()"
                [disabled]="myTeam().length === 0 || isGeneratingCounter()"
                class="btn btn-success"
                style="font-weight: 700;"
              >
                @if (isGeneratingCounter()) {
                  Calculando Optimo...
                } @else {
                  Generar Equipo Counter
                }
              </button>
            </div>
          </div>

          <!-- RESULTADOS DEL COUNTER TEAM -->
          @if (counterResult(); as result) {
            <div class="counter-results-container">
              <div class="card-header flex-between" style="margin-top: 1.5rem;">
                <div>
                  <h2>Equipo Counter Generado</h2>
                  <p class="card-description">
                    Emparejamiento exacto resuelto mediante Programacion Dinamica global sobre la matriz de tipos.
                  </p>
                </div>
                <div>
                  <span class="badge badge-success" style="font-size: 0.95rem; padding: 0.4rem 0.8rem;">
                    Ventaja Total: +{{ result.total_advantage }}
                  </span>
                </div>
              </div>

              <div class="counter-picks-grid">
                @for (pick of result.picks; track pick.enemy.id; let i = $index) {
                  <div class="counter-pick-card">
                    <!-- Caja del Rival -->
                    <div class="contender-box enemy">
                      <div class="flex-between">
                        <span class="text-muted" style="font-size: 0.75rem;">Rival #{{ i + 1 }}</span>
                        <span class="text-muted" style="font-size: 0.75rem;">Stats: {{ pick.enemy.stat_total }}</span>
                      </div>
                      <div class="pick-header">
                        @if (pick.enemy.sprite_url) {
                          <img [src]="pick.enemy.sprite_url" [alt]="pick.enemy.name" class="pokemon-pick-img" />
                        }
                        <div>
                          <h4 style="margin: 0.25rem 0;">#{{ pick.enemy.id }} {{ capitalize(pick.enemy.name) }}</h4>
                          <div>
                            <span class="type-badge" [class]="'type-' + pick.enemy.type1.name.toLowerCase()">
                              {{ capitalize(pick.enemy.type1.name) }}
                            </span>
                            @if (pick.enemy.type2) {
                              <span class="type-badge" [class]="'type-' + pick.enemy.type2.name.toLowerCase()">
                                {{ capitalize(pick.enemy.type2.name) }}
                              </span>
                            }
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Insignia VS y Ventaja -->
                    <div class="vs-badge-container">
                      <span class="vs-badge">VS</span>
                      <span
                        class="advantage-badge"
                        [class]="pick.advantage > 0 ? 'badge-success' : (pick.advantage === 0 ? 'badge-neutral' : 'badge-danger')"
                      >
                        {{ pick.advantage > 0 ? '+' : '' }}{{ pick.advantage }}
                      </span>
                    </div>

                    <!-- Caja del Counter Sugerido -->
                    <div class="contender-box counter">
                      <div class="flex-between">
                        <span class="text-success" style="font-weight: 700; font-size: 0.75rem;">Counter Asignado</span>
                        <span class="text-muted" style="font-size: 0.75rem;">Stats: {{ pick.counter.stat_total }}</span>
                      </div>
                      <div class="pick-header">
                        @if (pick.counter.sprite_url) {
                          <img [src]="pick.counter.sprite_url" [alt]="pick.counter.name" class="pokemon-pick-img" />
                        }
                        <div>
                          <h4 style="margin: 0.25rem 0;">#{{ pick.counter.id }} {{ capitalize(pick.counter.name) }}</h4>
                          <div>
                            <span class="type-badge" [class]="'type-' + pick.counter.type1.name.toLowerCase()">
                              {{ capitalize(pick.counter.type1.name) }}
                            </span>
                            @if (pick.counter.type2) {
                              <span class="type-badge" [class]="'type-' + pick.counter.type2.name.toLowerCase()">
                                {{ capitalize(pick.counter.type2.name) }}
                              </span>
                            }
                          </div>
                        </div>
                      </div>
                      <div class="matchup-metrics">
                        <div>Dano infligido: <strong>{{ pick.offense_multiplier }}x</strong> ({{ capitalize(pick.label) }})</div>
                        <div>Dano recibido: <strong>{{ pick.incoming_multiplier }}x</strong></div>
                      </div>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        </section>
      }

      <!-- VISTA 2: CATALOGO, FILTROS Y ANALISIS INDIVIDUAL -->
      @if (activeTab() === 'catalog') {
        <div class="grid-2-col">
          <!-- Seccion Principal: Listado y Filtros -->
          <section class="card">
            <div class="card-header">
              <h2>Catalogo de Pokemon</h2>
            </div>

            <div class="filters-bar">
              <div class="form-group">
                <label for="filter-generation">Generacion:</label>
                <select id="filter-generation" [(ngModel)]="selectedGeneration">
                  <option [ngValue]="null">Todas las generaciones</option>
                  @for (gen of generations(); track gen.number) {
                    <option [ngValue]="gen.number">
                      Gen {{ gen.number }} ({{ capitalize(gen.region) }}) - {{ gen.loaded }}/{{ gen.total_species }} cargados
                    </option>
                  }
                </select>
              </div>

              <div class="form-group">
                <label for="filter-type">Filtrar por Tipo:</label>
                <select id="filter-type" [(ngModel)]="selectedType">
                  <option value="">Todos los tipos</option>
                  @for (t of canonicalTypes; track t) {
                    <option [value]="t">{{ capitalize(t) }}</option>
                  }
                </select>
              </div>

              <div class="form-group btn-group-align">
                <button (click)="applyFilters()" class="btn btn-primary">Aplicar</button>
                <button (click)="resetFilters()" class="btn btn-secondary">Limpiar</button>
              </div>
            </div>

            <!-- Tabla de Pokemon -->
            <div class="table-responsive">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Pokemon</th>
                    <th>Tipo 1</th>
                    <th>Tipo 2</th>
                    <th>Stats</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  @if (isLoadingPokemon()) {
                    <tr>
                      <td colspan="6" class="text-center text-muted">Cargando datos...</td>
                    </tr>
                  } @else if (pokemonList().length === 0) {
                    <tr>
                      <td colspan="6" class="text-center text-muted">No se encontraron Pokemon.</td>
                    </tr>
                  } @else {
                    @for (p of pokemonList(); track p.id) {
                      <tr [class.selected]="selectedPokemon()?.id === p.id" (click)="selectPokemon(p.id)">
                        <td>#{{ p.id }}</td>
                        <td>
                          <div class="pokemon-name-col">
                            @if (p.sprite_url) {
                              <img [src]="p.sprite_url" [alt]="p.name" class="pokemon-sprite-thumb" />
                            }
                            <strong>{{ capitalize(p.name) }}</strong>
                          </div>
                        </td>
                        <td>
                          <span class="type-badge" [class]="'type-' + p.type1.name.toLowerCase()">
                            {{ capitalize(p.type1.name) }}
                          </span>
                        </td>
                        <td>
                          @if (p.type2) {
                            <span class="type-badge" [class]="'type-' + p.type2.name.toLowerCase()">
                              {{ capitalize(p.type2.name) }}
                            </span>
                          } @else {
                            <span class="text-muted">-</span>
                          }
                        </td>
                        <td><strong>{{ p.stat_total }}</strong></td>
                        <td>
                          <div style="display: flex; gap: 0.25rem;">
                            <button
                              (click)="selectPokemon(p.id); $event.stopPropagation()"
                              class="btn btn-sm btn-secondary"
                            >
                              Detalles
                            </button>
                            <button
                              (click)="addPokemonToTeam(p); $event.stopPropagation()"
                              [disabled]="myTeam().length >= 6 || isAlreadyInTeam(p.id)"
                              class="btn btn-sm btn-primary"
                            >
                              + Equipo
                            </button>
                          </div>
                        </td>
                      </tr>
                    }
                  }
                </tbody>
              </table>
            </div>

            <!-- Paginacion -->
            <div class="pagination-bar">
              <div class="pagination-info">{{ paginationText() }}</div>
              <div class="pagination-buttons">
                <button
                  (click)="prevPage()"
                  [disabled]="offset() === 0 || selectedType !== ''"
                  class="btn btn-sm btn-secondary"
                >
                  Anterior
                </button>
                <button
                  (click)="nextPage()"
                  [disabled]="offset() + limit() >= totalPokemon() || selectedType !== ''"
                  class="btn btn-sm btn-secondary"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </section>

          <!-- Panel Lateral: Detalle, Percentil, Matchup y Top Ranking -->
          <aside class="sidebar-col">
            <!-- Detalle de Pokemon -->
            <section class="card">
              <div class="card-header">
                <h2>Detalle de Pokemon</h2>
              </div>
              @if (selectedPokemon(); as current) {
                <div>
                  @if (current.sprite_url) {
                    <img [src]="current.sprite_url" [alt]="current.name" class="pokemon-artwork-large" />
                  }
                  <div class="flex-between">
                    <h3>#{{ current.id }} {{ capitalize(current.name) }}</h3>
                    <div>
                      <span class="type-badge" [class]="'type-' + current.type1.name.toLowerCase()">
                        {{ capitalize(current.type1.name) }}
                      </span>
                      @if (current.type2) {
                        <span class="type-badge" [class]="'type-' + current.type2.name.toLowerCase()">
                          {{ capitalize(current.type2.name) }}
                        </span>
                      }
                    </div>
                  </div>

                  <div class="stats-grid">
                    <div class="stat-box"><div class="stat-name">HP</div><div class="stat-val">{{ current.hp }}</div></div>
                    <div class="stat-box"><div class="stat-name">Ataque</div><div class="stat-val">{{ current.attack }}</div></div>
                    <div class="stat-box"><div class="stat-name">Defensa</div><div class="stat-val">{{ current.defense }}</div></div>
                    <div class="stat-box"><div class="stat-name">Ataque Sp.</div><div class="stat-val">{{ current.sp_attack }}</div></div>
                    <div class="stat-box"><div class="stat-name">Defensa Sp.</div><div class="stat-val">{{ current.sp_defense }}</div></div>
                    <div class="stat-box"><div class="stat-name">Velocidad</div><div class="stat-val">{{ current.speed }}</div></div>
                  </div>

                  <div class="flex-between">
                    <strong>Total de Estadisticas:</strong>
                    <span class="badge badge-neutral">{{ current.stat_total }}</span>
                  </div>
                  <div class="flex-between mt-3">
                    <strong>Percentil de Poder:</strong>
                    <span class="badge badge-success">{{ selectedPercentile() }}%</span>
                  </div>

                  <div class="mt-3">
                    <button
                      (click)="addPokemonToTeam(current)"
                      [disabled]="myTeam().length >= 6 || isAlreadyInTeam(current.id)"
                      class="btn btn-primary btn-block"
                    >
                      Agregar este Pokemon al Equipo
                    </button>
                  </div>
                </div>
              } @else {
                <p class="text-muted text-center">Selecciona un Pokemon de la tabla para ver sus detalles.</p>
              }
            </section>

            <!-- Calculadora de Matchup Individual -->
            <section class="card">
              <div class="card-header">
                <h2>Calculadora de Matchup Individual</h2>
              </div>
              <div class="form-group">
                <label for="matchup-type">Tipo Atacante:</label>
                <select id="matchup-type" [(ngModel)]="attackerType">
                  @for (t of canonicalTypes; track t) {
                    <option [value]="t">{{ capitalize(t) }}</option>
                  }
                </select>
              </div>
              <button
                (click)="calculateMatchup()"
                [disabled]="!selectedPokemon() || isCalculatingMatchup()"
                class="btn btn-primary btn-block mt-3"
              >
                Calcular Dano contra Seleccionado
              </button>

              @if (matchupResult(); as matchup) {
                <div class="matchup-box mt-3">
                  <div>
                    Ataque <strong>{{ capitalize(matchup.attacker_type) }}</strong> vs <strong>{{ capitalize(matchup.defender) }}</strong>:
                  </div>
                  <div class="flex-between mt-3">
                    <span>Multiplicador de Dano:</span>
                    <span class="badge" [class]="matchupBadgeClass(matchup.multiplier)">
                      {{ matchup.multiplier }}x ({{ capitalize(matchup.label) }})
                    </span>
                  </div>
                </div>
              }
            </section>

            <!-- Ranking Top Power -->
            <section class="card">
              <div class="card-header flex-between">
                <h2>Top Ranking de Poder</h2>
                <button (click)="loadTopRanking()" class="btn btn-sm btn-secondary">Actualizar</button>
              </div>
              <div class="table-responsive">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Nombre</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    @if (topRanking().length === 0) {
                      <tr>
                        <td colspan="3" class="text-center text-muted">Cargando ranking...</td>
                      </tr>
                    } @else {
                      @for (item of topRanking(); track item.name; let i = $index) {
                        <tr>
                          <td><strong>{{ i + 1 }}</strong></td>
                          <td>{{ capitalize(item.name) }}</td>
                          <td><span class="badge badge-neutral">{{ item.score }} pts</span></td>
                        </tr>
                      }
                    }
                  </tbody>
                </table>
              </div>
            </section>
          </aside>
        </div>
      }
    </main>

    <footer class="footer">
      <div class="container text-center">
        <p>NewMonolioPokemon - Frontend en Angular con Generador de Counter Team</p>
      </div>
    </footer>
  `,
})
export class App implements OnInit {
  private http = inject(HttpClient);

  // Configuracion API
  apiUrl = 'http://localhost:8000/api/v1';

  // Pestana activa
  activeTab = signal<'counter' | 'catalog'>('counter');

  // Estados de salud
  livenessStatus = signal('No verificado');
  livenessClass = signal('badge badge-neutral');
  readinessStatus = signal('No verificado');
  readinessClass = signal('badge badge-neutral');
  totalLoaded = signal(0);
  totalLoadedClass = signal('badge badge-neutral');

  // Tipos canonicos
  readonly canonicalTypes: string[] = [
    'normal', 'fighting', 'flying', 'poison', 'ground', 'rock',
    'bug', 'ghost', 'steel', 'fire', 'water', 'grass',
    'electric', 'psychic', 'ice', 'dragon', 'dark', 'fairy',
  ];

  // Generaciones y filtros
  generations = signal<GenerationRead[]>([]);
  selectedGeneration: number | null = null;
  selectedType = '';

  // Paginacion y datos
  pokemonList = signal<PokemonRead[]>([]);
  totalPokemon = signal(0);
  limit = signal(20);
  offset = signal(0);
  isLoadingPokemon = signal(false);

  // Detalle y percentil
  selectedPokemon = signal<PokemonRead | null>(null);
  selectedPercentile = signal<number>(0);

  // Matchup individual
  attackerType = 'fire';
  isCalculatingMatchup = signal(false);
  matchupResult = signal<MatchupRead | null>(null);

  // Top ranking
  topRanking = signal<TopPokemonRead[]>([]);

  // Team Builder & Counter Team
  myTeam = signal<PokemonRead[]>([]);
  quickAddInput = '';
  excludeMyTeam = false;
  isGeneratingCounter = signal(false);
  teamError = signal<string | null>(null);
  counterResult = signal<CounterTeamRead | null>(null);

  ngOnInit(): void {
    this.checkHealth();
    this.loadPokemon();
    this.loadTopRanking();
  }

  private cleanUrl(): string {
    let url = this.apiUrl.trim();
    while (url.endsWith('/')) {
      url = url.slice(0, -1);
    }
    return url;
  }

  capitalize(str: string): string {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  paginationText(): string {
    if (this.selectedType) {
      return `Mostrando ${this.pokemonList().length} Pokemon de tipo ${this.capitalize(this.selectedType)}`;
    }
    const start = this.totalPokemon() === 0 ? 0 : this.offset() + 1;
    const end = Math.min(this.offset() + this.limit(), this.totalPokemon());
    return `Mostrando ${start} - ${end} de ${this.totalPokemon()}`;
  }

  matchupBadgeClass(multiplier: number): string {
    if (multiplier >= 2.0) return 'badge-danger';
    if (multiplier === 0) return 'badge-neutral';
    if (multiplier < 1.0) return 'badge-success';
    return 'badge-neutral';
  }

  async checkHealth(): Promise<void> {
    const base = this.cleanUrl();
    this.livenessStatus.set('Verificando...');
    this.livenessClass.set('badge badge-neutral');
    this.readinessStatus.set('Verificando...');
    this.readinessClass.set('badge badge-neutral');

    try {
      const live = await firstValueFrom(this.http.get<{ status: string }>(`${base}/health`));
      this.livenessStatus.set(live.status || 'OK');
      this.livenessClass.set('badge badge-success');
    } catch {
      this.livenessStatus.set('Sin conexion');
      this.livenessClass.set('badge badge-danger');
    }

    try {
      const ready = await firstValueFrom(this.http.get<{ database: string }>(`${base}/health/ready`));
      this.readinessStatus.set(ready.database === 'ok' ? 'OK' : 'Error');
      this.readinessClass.set('badge badge-success');
    } catch {
      this.readinessStatus.set('Desconectado');
      this.readinessClass.set('badge badge-danger');
    }

    this.loadGenerations();
  }

  async loadGenerations(): Promise<void> {
    const base = this.cleanUrl();
    try {
      const gens = await firstValueFrom(this.http.get<GenerationRead[]>(`${base}/generations`));
      this.generations.set(gens);
      const total = gens.reduce((sum, g) => sum + g.loaded, 0);
      this.totalLoaded.set(total);
      this.totalLoadedClass.set(total > 0 ? 'badge badge-success' : 'badge badge-warning');
    } catch (err) {
      console.error('Error al cargar generaciones:', err);
    }
  }

  async loadPokemon(): Promise<void> {
    const base = this.cleanUrl();
    this.isLoadingPokemon.set(true);

    try {
      if (this.selectedType) {
        const url = `${base}/pokemon/by-type/${encodeURIComponent(this.selectedType.toLowerCase())}?limit=100`;
        const items = await firstValueFrom(this.http.get<PokemonRead[]>(url));
        this.pokemonList.set(items);
        this.totalPokemon.set(items.length);
      } else {
        let url = `${base}/pokemon?limit=${this.limit()}&offset=${this.offset()}`;
        if (this.selectedGeneration !== null) {
          url += `&generation=${this.selectedGeneration}`;
        }
        const page = await firstValueFrom(this.http.get<PageResponse<PokemonRead>>(url));
        this.pokemonList.set(page.items);
        this.totalPokemon.set(page.total);
      }
    } catch (err) {
      console.error('Error al cargar pokemon:', err);
      this.pokemonList.set([]);
    } finally {
      this.isLoadingPokemon.set(false);
    }
  }

  async selectPokemon(id: number): Promise<void> {
    const base = this.cleanUrl();
    this.matchupResult.set(null);

    try {
      const [pokemon, perc] = await Promise.all([
        firstValueFrom(this.http.get<PokemonRead>(`${base}/pokemon/${id}`)),
        firstValueFrom(this.http.get<{ percentile: number }>(`${base}/pokemon/${id}/percentile`)),
      ]);
      this.selectedPokemon.set(pokemon);
      this.selectedPercentile.set(perc.percentile);
    } catch (err) {
      console.error('Error al seleccionar pokemon:', err);
    }
  }

  async calculateMatchup(): Promise<void> {
    const current = this.selectedPokemon();
    if (!current) return;

    const base = this.cleanUrl();
    this.isCalculatingMatchup.set(true);

    try {
      const result = await firstValueFrom(
        this.http.get<MatchupRead>(`${base}/pokemon/${current.id}/matchup/${this.attackerType.toLowerCase()}`)
      );
      this.matchupResult.set(result);
    } catch (err) {
      console.error('Error al calcular matchup:', err);
    } finally {
      this.isCalculatingMatchup.set(false);
    }
  }

  async loadTopRanking(): Promise<void> {
    const base = this.cleanUrl();
    try {
      const ranking = await firstValueFrom(this.http.get<TopPokemonRead[]>(`${base}/pokemon/top?limit=10`));
      this.topRanking.set(ranking);
    } catch (err) {
      console.error('Error al cargar top ranking:', err);
    }
  }

  applyFilters(): void {
    this.offset.set(0);
    this.loadPokemon();
  }

  resetFilters(): void {
    this.selectedGeneration = null;
    this.selectedType = '';
    this.offset.set(0);
    this.loadPokemon();
  }

  nextPage(): void {
    if (this.offset() + this.limit() < this.totalPokemon()) {
      this.offset.update((v) => v + this.limit());
      this.loadPokemon();
    }
  }

  prevPage(): void {
    if (this.offset() >= this.limit()) {
      this.offset.update((v) => v - this.limit());
      this.loadPokemon();
    }
  }

  // --- LOGICA DE EQUIPO Y COUNTER TEAM ---

  isAlreadyInTeam(pokemonId: number): boolean {
    return this.myTeam().some((p) => p.id === pokemonId);
  }

  addPokemonToTeam(pokemon: PokemonRead): void {
    this.teamError.set(null);
    if (this.myTeam().length >= 6) {
      this.teamError.set('El equipo ya tiene el maximo permitido de 6 Pokemon.');
      return;
    }
    if (this.isAlreadyInTeam(pokemon.id)) {
      this.teamError.set(`'${this.capitalize(pokemon.name)}' ya se encuentra en el equipo.`);
      return;
    }
    this.myTeam.update((team) => [...team, pokemon]);
  }

  removePokemonFromTeam(index: number): void {
    this.teamError.set(null);
    this.myTeam.update((team) => team.filter((_, i) => i !== index));
    if (this.myTeam().length === 0) {
      this.counterResult.set(null);
    }
  }

  clearTeam(): void {
    this.myTeam.set([]);
    this.counterResult.set(null);
    this.teamError.set(null);
  }

  async addQuickPokemon(): Promise<void> {
    const input = this.quickAddInput.trim();
    if (!input) return;

    const base = this.cleanUrl();
    this.teamError.set(null);

    try {
      const pokemon = await firstValueFrom(
        this.http.get<PokemonRead>(`${base}/pokemon/${encodeURIComponent(input.toLowerCase())}`)
      );
      this.addPokemonToTeam(pokemon);
      this.quickAddInput = '';
    } catch (err: any) {
      if (err.status === 404) {
        this.teamError.set(`No se encontro el Pokemon '${input}'. Verifica el nombre o numero.`);
      } else {
        this.teamError.set(`Error al buscar Pokemon '${input}': ${err.message || 'Error de conexion'}`);
      }
    }
  }

  loadRandomTeam(): void {
    this.clearTeam();
    const available = [...this.pokemonList()];
    if (available.length === 0) return;

    const sample = available.slice(0, Math.min(4, available.length));
    this.myTeam.set(sample);
  }

  async generateCounterTeam(): Promise<void> {
    const team = this.myTeam();
    if (team.length === 0) {
      this.teamError.set('Debes ingresar al menos 1 Pokemon en el equipo.');
      return;
    }

    const base = this.cleanUrl();
    this.isGeneratingCounter.set(true);
    this.teamError.set(null);

    try {
      let params = new HttpParams();
      for (const member of team) {
        params = params.append('team', member.id.toString());
      }
      if (this.excludeMyTeam) {
        params = params.set('exclude_team', 'true');
      }

      const result = await firstValueFrom(
        this.http.get<CounterTeamRead>(`${base}/team/counters`, { params })
      );
      this.counterResult.set(result);
    } catch (err: any) {
      if (err.status === 409) {
        this.teamError.set('No hay suficientes Pokemon en la base de datos para generar un equipo counter sin repetir.');
      } else if (err.status === 404) {
        this.teamError.set('Uno o mas miembros del equipo no fueron encontrados.');
      } else {
        this.teamError.set(`Error al generar equipo counter: ${err.message || 'Fallo de conexion'}`);
      }
    } finally {
      this.isGeneratingCounter.set(false);
    }
  }
}
