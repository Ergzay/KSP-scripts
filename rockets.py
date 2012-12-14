from __future__ import division # / means float div always

import math
from numbers import Number
import heapq
from LinkedList import LinkedList
from array import array

# Following pretty much an optimal climb slope to a 100km orbit at Kerbin,
# here's a correspondence between deltaV and altitude.  I haven't figured
# out how to calculate this correctly for other planets... TODO
climbSlope = [
    # deltaV, altitude
    (287, 923),
    (509, 2117),
    (731, 3461),
    (957, 5044),
    (1188, 6900),
    (1437, 9169),
    (1723, 12138),
    (2102, 16248),
    (2729, 22722),
    (3069, 32500)
]

# Atmospheric pressure at a body is k e^{altitude/scale}
# Kerbin is 1*e^{altitude/5000}, Duna is 0.2e^{altitude/3000}, etc.
class planet(object):
    def __init__(self, name, base, scale):
        self.name = name
        self.base = base
        self.scale = scale

    def optimalDeltaV(self, altitude):
        """
        Return the deltaV needed to get to the given altitude on an optimal
        glide slop.  This means we have achieved terminal velocity.

        Return None if deltaV puts us outside the atmosphere.
        """
        for i in range(len(climbSlope)):
            if climbSlope[i][1] == altitude: return climbSlope[i][0]
            elif climbSlope[i][1] > altitude:
                # linearly (!) interpolate
                if i == 0:
                    alpha = altitude / climbSlope[i][1]
                    return alpha * climbSlope[i][0]
                else:
                    alpha = ((altitude - climbSlope[i-1][1]) /
                            (climbSlope[i][1] - climbSlope[i-1][1]))
                    return (alpha * climbSlope[i][0] +
                        (1-alpha) * climbSlope[i-1][0])
        return None

    def optimalAltitude(self, deltaV):
        """
        Return the altitude after burning deltaV on an optimal climb slope.
        This means we have achieved terminal velocity, and have burned an equal
        amount on gravity and drag.

        Return None if deltaV puts us outside the atmosphere.
        """
        # TODO: I don't understand the math yet, so just look it up.
        for i in range(len(climbSlope)):
            if climbSlope[i][0] == deltaV: return climbSlope[i][1]
            elif climbSlope[i][0] > deltaV:
                # linearly (!) interpolate
                if i == 0:
                    alpha = deltaV / climbSlope[i][0]
                    return alpha * climbSlope[i][1]
                else:
                    alpha = ((deltaV - climbSlope[i-1][0]) /
                            (climbSlope[i][0] - climbSlope[i-1][0]))
                    return (alpha * climbSlope[i][1] +
                        (1-alpha) * climbSlope[i-1][1])
        return None

    def pressure(self, altitude):
        """
        Return the atmospheric pressure in Atm, which is a factor for
        interpolating the Isp of engines.
        """
        if altitude is None: p = 0
        else: p = self.base * math.exp(-altitude / self.scale)
        #print ("pressure at %s: %g" % (altitude, p))
        return p

kerbin = planet("kerbin", 1, 5000)

##############################
## Available engines
class engine(object):
    def __init__(self, name, IspAtm, IspVac, mass, thrust,
            vectoring = False, radial = False, large = False):
        self.name = name
        self.IspAtm = IspAtm        # seconds
        self.IspVac = IspVac        # seconds
        self.mass = mass            # tonnes
        self.thrust = thrust        # kN
        self.vectoring = vectoring  # true or false
        self.radial = radial        # true of false
        self.large = large          # true: 2m, false: 1m (can use bi/tricoupler)

    def Isp(self, altitude):
        # Assumption: Isp is in a linear correspondence with pressure.
        pressure = kerbin.pressure(altitude)
        Isp = pressure * self.IspAtm + (1.0 - pressure) * self.IspVac
        return Isp

    def __str__(self):
        return self.name

g_engines = [
    # We have a none engine for fuel-only stages in asparagus staging.
    # It has non-zero Isp to avoid divide-by-zero.  Make it radial,
    # so that we can have radial engines above and we needn't add towers.
    engine("none",        1,    1,    0,         0, radial=True),

    # Real engines.  I'm using the vaccum values rather than atmospheric
    # here; that's a TODO.
    # That means I can't add the jet and ramjet, either.
    engine("24-77",     250, 300,    0.09,     20, vectoring=True, radial=True),
    engine("Aerospike", 388, 390,    1.5,     175),
    engine("LV-1",      220, 290,    0.03,      1.5),
    engine("LV-909",    300, 390,    0.5,      50, vectoring=True),
    engine("LV-N",      220, 800,    2.25,     60, vectoring=True),
    engine("LV-T30",    320, 370,    1.25,    215),
    engine("LV-T45",    320, 370,    1.5,     200, vectoring=True),
    engine("Mainsail",  280, 330,    6,      1500, vectoring=True, large=True),
    engine("Mark 55",   290, 320,    0.9,     120, vectoring=True, radial=True),
    engine("Poodle",    270, 390,    2.5,     220, vectoring=True, large=True),

    # The ion engine is a bit off: we need a *lot* of power for it,
    # which starts to add more mass than just the 0.25.  Also, the
    # dry mass is much more than 1/4 of the propellant, and the number
    # of containers starts to matter.  So just ignore it.
    #engine("ion",      4200,4200,    0.25,      0.5),

    # Note: solid-fuel rockets aren't handled correctly yet.
    # engine("Sepratron", 100,    0.15,     20, solid=9),
    # engine("RT-10",     240,    0.5,     250, solid=433),
    # engine("BACC",      250,    1.75,    300, solid=850),
]

#class tank(object):
#    def __init__(self, name, drymass, liquid, oxidizer):
#        """
#        Liquid and oxidizer in 5kg units (!?); drymass in tonnes.
#        """
#        self.name = name
#        self.drymass = drymass
#        self.propellant = drymass + (liquid+oxidizer) * 0.005
#        self.fullmass = drymass + self.propellant

## Store the tanks sorted by capacity.  But only the big tanks; the two
## small tanks I don't feel like handling.
#tanks = [
#    tank("Jumbo-64", 4, 2880, 3520),
#    tank("X200-32", 2, 1440, 1760),
#    tank("X200-16", 1, 720, 880),
#    tank("FL-T800 or X200-8", 0.5, 360, 440),
#    tank("FL-T400", 0.25, 180, 220),
#    tank("FL-T200", 0.125, 90, 110),
#    tank("Oscar-B", 0.015, 5.735, 7),
#    tank("ROUND-8", 0.025, 10, 12.2),
#]

##############################
## Tsiokolvsky rocket equation

g0 = 9.80665
beta = 8 # ratio of propellant mass : dry mass in the big stock tanks.

def alpha(deltaV, Isp):
    return math.exp(deltaV / (Isp * g0))

def propellantMass(deltaV, Isp, m0):
    return m0 * (alpha(deltaV, Isp) - 1)

def burnMass(deltaV, Isp, m0):
    """
    Return the mass of propellant and tanks that we'll need to burn,
    assuming tanks hold 8 times their mass.  The assumption is false
    for some of the smallest tanks.

    Return None if it is impossible to achieve the deltaV with that given
    Isp given the mass of the tanks.

    deltaV: m/s
    Isp: s
    m0: tonnes, should include payload, engines, decouplers, but
        not the propellant and tanks we're using.

    return (propellant mass, tank mass)
    """
    # The amount of fuel we need is derived from the ideal rocket
    # equation.  Let alpha = e^{deltaV/Isp.g0}, beta = ratio of
    # propellant to dry mass of a tank.  Then:
    # tankMass = (alpha-1) * payload / (1 - alpha + beta)
    # Where the relevant payload here includes engines and decouplers.
    # Clearly, if (1-alpha+beta) <= 0 then we are in an impossible
    # state: this corresponds to needing infinite fuel.
    a = alpha(deltaV, Isp)
    beta = 8 # TODO: handle the smaller, less efficient tanks too!
    if 1 - a + beta <= 0: raise WeakEngineException(Isp)
    tankMass = m0 * (a - 1) / (1 - a + beta)
    propMass = tankMass * beta
    return (propMass, tankMass)


def burnTime(deltaV, Isp, thrust, m0):
    # the mass flow rate of an engine is thrust / (Isp * g0)
    # the mass of the burn is defined above, divide to get time.
    mass = propellantMass(deltaV, Isp, m0)
    rate = thrust / (Isp * g0)
    return mass / rate

def combineIsp(engines, altitude):
    """
    Given a dictionary mapping engine -> count, compute the
    Isp of the system at the given altitude.

    This is the weighted sum of the impulses of each type, with weights
    based off the relative mass flow rate of the engines.
    """
    # the mass flow rate of an engine is thrust / (Isp * g0)
    # so the mass is sum(num_i * thrust_i / (Isp_i * g0))
    # the relative mass of engine type j is
    #   [num_j*thrust_j / (Isp_j*g0)] / sum(...)
    # and we cancel out the g0.
    def numerator(engcount):
        (engine, count) = engcount
        return count * engine.thrust / engine.Isp(altitude)
    flows = [ numerator(x) for x in engines.iteritems() ]
    total = sum(flows)
    if total == 0: return 0
    alpha = [ f / total for f in flows ]
    weightedIsp = [
        engine.Isp(altitude) * a
            for (engine, a) in zip(engines.iterkeys(), alpha)
    ]
    return sum(weightedIsp)

# combine 3x nuke and sail
# print combineIsp( [(engines[1], 1), (engines[2], 3)] )


##############################
#
class WeakEngineException(Exception):
    def __init__(self, Isp): self.Isp = Isp
class MoarBoosters(Exception): pass

class stage(object):
    """
    """
    def __init__(self, deltaV, payload, engineType, nEngines, laterStages,
                numTowers, altitude):

        # Calculate the effective Isp including later stages.
        allEngines = { engineType : nEngines }
        thrust = engineType.thrust * nEngines
        if engineType.vectoring:
            vectoringThrust = engineType.thrust * nEngines
        else:
            vectoringThrust = 0

        if not laterStages:
            Isp = engineType.Isp(altitude)
        else:
            for s in laterStages:
                if s.engineType in allEngines:
                    allEngines[s.engineType] += s.numEngines
                else:
                    allEngines[s.engineType] = s.numEngines
            Isp = combineIsp(allEngines, altitude)
            thrust += laterStages.head.thrust
            vectoringThrust += laterStages.head.vectoringThrust

        # Calculate masses.
        # Engine mass is specified already.  We only count the engines
        # being dumped in this stage.
        # We add 0.3 for decouplers, struts, fuel lines.
        # Dry mass is payload, engines, and empty tanks.
        engineMass = engineType.mass * nEngines
        decouplerMass = 0.3 * numTowers
        dryMassNoTanks = payload + engineMass + decouplerMass

        # Get the propellant mass, and distribute it over the towers.
        #
        # TODO: handle SRBs.
        (propMass, tankMass) = burnMass(deltaV, Isp, dryMassNoTanks)

        # Round up to fit an integer number of tanks on each tower.
        #
        # By the rocket equation, bringing extra unburned mass is OK, we'll
        # just finish our burn without finishing our fuel.  We can dump the
        # excess, or use it for the next stage burn.  So we round up to an
        # integer fuel mass per tower.
        propMass = math.ceil(propMass / numTowers) * numTowers
        tankMass = propMass / beta

        dryMass = dryMassNoTanks + tankMass
        fullMass = dryMass + propMass

        # Store a bunch of data (do we really need it all?)
        # Many of the fields are packed into a python array of floats,
        # which we have to create first.
        self._data = array('f', range(len(self._attrindices)))
        self.deltaV = deltaV
        self.payload = payload
        self.engineType = engineType
        self.numEngines = nEngines
        self.numTowers = numTowers
        self.asparagus = bool(laterStages)
        self.engineMass = engineMass
        self.decouplerMass = decouplerMass
        self.propellantMass = propMass
        self.dryMass = dryMass
        self.fullMass = fullMass
        self.Isp = Isp
        self.burnTime = burnTime(deltaV, Isp, thrust, dryMass)
        self.thrust = thrust
        self.vectoringThrust = vectoringThrust

    _attrindices = dict( (name, i) for (i, name) in enumerate([
        'deltaV', 'payload', 'numEngines', 'numTowers', 'asparagus',
        'engineMass', 'decouplerMass', 'propellantMass', 'dryMass', 
        'fullMass', 'Isp', 'burnTime', 'thrust', 'vectoringThrust'
    ]))

    def __getattr__(self, attr):
        indices = self._attrindices
        if attr in indices:
            return self._data[indices[attr]]
        else:
            raise AttributeError

    def __setattr__(self, attr, value):
        indices = self._attrindices
        if attr in indices:
            self._data[indices[attr]] = value
        else:
            object.__setattr__(self, attr, value)

    def __str__(self):
        return (
        "mass %g T,%s %d x %d %s and %g T fuel, %.2fs burn at %g kN (%.2f m/s^2), Isp %d"
        %   (self.fullMass,
             " asparagus" if self.asparagus else "",
             self.numTowers,
             self.numEngines / self.numTowers,
             self.engineType.name,
             self.propellantMass / self.numTowers,
             self.burnTime,
             self.thrust,
             self.thrust / self.fullMass,
             self.Isp)
        )

class burnRequirement(object):
    """
    Defines requirements for a burn.
    """
    def __init__(self, burnTime = None, acceleration = None):
        self.burnTime = burnTime
        self.acceleration = acceleration

    def satisfiedBy(self, stage):
        """
        Given a proposed stage, does it satisfy the burn requirements?
        """
        if self.burnTime and stage.burnTime > self.burnTime: return False
        if self.acceleration:
            # thrust is in kN, mass in tonnes, so the ratio is m/s^2
            accel = stage.thrust / stage.fullMass
            if accel < self.acceleration: return False
        # Nothing failed => success.
        return True

    def __str__(self):
        if self.burnTime is None and self.acceleration is None:
            return "unlimited burn"
        elif self.burnTime is None:
                return ("min %g m/s^2" % self.acceleration)
        elif self.acceleration is None:
            return ("max %gs burn" % self.burnTime)
        else:
            return ("min %g m/s^2, max %gs burn"
                        % (self.acceleration, self.burnTime))

def evalStage(symmetry, deltaV, payload, engineType, altitude,
              burnRequirement = None, laterStages = []):
    """
    Given an engine type, a maximum burn time,
    deltaV, and payload, return the stage description.
    This is where we choose the number of engines (the type is given).
    We maintain the desired symmetry.
    If we are asparagus staging, specify the list of later stages we can
    use.

    If the engine is too wimpy, return None.

    We are required to have at least 25% of our thrust be vectoring at all
    times.  If we're violating that, return None.
    """
    # If we aren't asparagus staging (or this is the first stage), we need
    # a vectoring engine.
    if not laterStages and not engineType.vectoring:
        return None

    # How many towers do we have?
    # If we only have no engines, or only radial engines above, we can fit
    # on one tower.  Otherwise we have a number of towers according to
    # symmetry.
    numTowers = 1
    for s in laterStages:
        if not s.engineType.radial:
            numTowers = symmetry

    # Count up how many engines we might be able to use.
    # TODO: I'm not allowing making a tower with side towers.  That limits
    # a lot of things (particularly large loads).
    # TODO: I'm not allowing mixing engine types.  In particular, you could
    # have a stage with both standard and radial engines; or if you have
    # more than one tower, you could use a bicoupler or tricoupler with 2
    # types of engines.
    if engineType.large:
        # We can only fit one engine on each tower.
        numEngines = [ numTowers ]
        extraMass = [ 0 ]
    elif engineType.radial:
        # If we have one tower, we need to maintain symmetry.
        # Otherwise, we can use 1 to 16 per tower.
        if numTowers == 1:
            maxEngines = int(math.ceil(16/symmetry))
            numEngines = [ x * symmetry for x in range(1, maxEngines + 1) ]
        else:
            numEngines = [ x * numTowers for x in range(1,17) ]
        extraMass = [ 0 for _ in range(len(numEngines)) ]
    else:
        # We can use 1, 2 (on a bicoupler), 3 (on a tricoupler), or 4 (on
        # chained bicouplers).  I suppose we could do crazy things too,
        # let's ignore that.
        numEngines = [ numTowers, 2*numTowers, 3*numTowers, 4*numTowers ]
        extraMass  = [ 0,
            0.1 * numTowers,  # bicoupler
            0.15 * numTowers, # tricoupler
            0.3 * numTowers ] # bicoupler with 2 bicouplers under it

    for (n, xmass) in zip(numEngines, extraMass):
        try:
            s = stage(deltaV, payload + xmass, engineType, n, laterStages,
                      numTowers, altitude)
        except WeakEngineException, e:
            # Our Isp is too low to get anywhere.  Check if adding more
            # engines will improve the Isp.
            if e.Isp < engineType.Isp(altitude):
                continue # Adding more may help.
            else:
                return None # Adding more will get us nowhere.

        if s.vectoringThrust < 0.25 * s.thrust:
            if engineType.vectoring: continue
            else:
                # We need more engines, but we also need to vector; try
                # another type.
                return None

        if not burnRequirement.satisfiedBy(s):
            # Not enough thrust, add more thrust.
            continue

        # If we get here, we like the stage.
        return s

    # If we get here, the engine is too wimpy to get there fast enough even
    # with 100 of them.
    return None


def designStage(symmetry, deltaV, payload, altitude,
                laterStages = [],
                burnRequirement = None):
    """
    Given a payload mass (i.e. the mass of the next stage), calculate the
    type of engine, the number of engines needed if we have a limited burn
    time, and the propellant mass.

    We are required to have at least 25% of our thrust be vectoring at all
    times.

    Limitation: we only think of adding one type of engine, no mixing.

    deltaV in m/s
    payload in tonnes
    burnRequirement optional, an instance of a 'burn'
    laterStages: list of later stages whose thrust we can use in asparagus
        staging.
    """
    stages = [ evalStage(symmetry, deltaV, payload, engine, altitude,
                            burnRequirement, laterStages)
                for engine in g_engines ]
    return sorted([ x for x in stages if x is not None],
                  key=lambda x: x.fullMass)

##############################
#
# We have n stages.
# We need a given total deltaV (in m/s), or a list of deltaV, one per
# stage.
# We have a given payload (in tonnes).
# We never fall below a given thrust:mass ratio.
# We can only use the engines in the map above.
# Tanks have arbitrary size (falsehood!), carry 4:1 prop:tank mass.
# Each burn must occur with the specified burn time, if specified.
#   None means we have unlimited burn time.
#   A number means to use that burn time for each stage.
#   A list specifies the burn time per stage (each one is a number or
#   None).
# We can use asparagus staging.  A false value means we don't, a true
#   value means we do.  If it's true, then at each stage we use all the
#   engines above.  Limitation: each stage only uses one type of engine,
#   though different stages can use different engines.
#
# Output the number and type of engines, and the
# number of tons of propellant at each stage.

class burnProfile(object):
    """
    Represent a set of burns to be done:
    * The number of burns.
    * The deltaV of each burn.
    * The altitude we'll be at for each burn.
    * The requirements (time or acceleration) for each part of the burns.
    * To help the search, the best Isp available at each altitude.

    The requirements come in in order from the ground up.
    We store them more conveniently for the search, from the last stage
    down.

    Use burnRequirements, deltaV, and altitude.
    """
    def __init__(self, n, deltaV,
            burnRequirements = None, startAltitude = 0):
        if burnRequirements is None:
            burnRequirements = [ None for _ in range(n) ]
        elif isinstance(burnRequirements, burnRequirement):
            burnRequirements = [ burnRequirements for _ in range(n) ]
        burnRequirements = [
            r if r is not None else burnRequirement() for r in burnRequirements
        ]

        if isinstance(deltaV, Number):
            deltaV = [ deltaV/n for _ in range(n) ]

        # The assumption is that prior stages (not yet designed) will hit the
        # deltaV on the nose, which means that in practice we're pessimistic
        # about our altitude.
        altitude = []
        lastDV = kerbin.optimalDeltaV(startAltitude)
        for dV in deltaV:
            altitude.append(kerbin.optimalAltitude(lastDV))
            lastDV = lastDV + dV
        #print ("altitudes: %s" % altitude)

        # For each altitude, figure out what is the best Isp we can possible
        # achieve.
        ispMaxEngine = [
            max(g_engines, key = lambda x: x.Isp(alt)) for alt in altitude
        ]
        ispMax = [ x.Isp(alt) for (x, alt) in zip(ispMaxEngine, altitude) ]

        # All those were in order from the surface up.
        # Now, we'll be working from the destination down, so reverse the
        # arrays.
        assert len(deltaV) == len(altitude) == len(burnRequirements)
        self.deltaV = list(reversed(deltaV))
        self.altitude = list(reversed(altitude))
        self.burnRequirements = list(reversed(burnRequirements))
        self.maxIsp = list(reversed(ispMax))

class partialSolution(object):
    """
    Set up a partial solution with the given upper stages already
    selected.  Keep track of the required symmetry.
    If this is the first stage, set the payload.
    """
    def __init__(self, profile, stages, symmetry, payload = None):
        self.profile  = profile
        self.stages   = stages
        self.symmetry = symmetry
        self.complete = (len(stages) == len(profile.deltaV))
        self.currentMass = stages.head.fullMass if stages else payload
        if self.complete:
            self.bestMass = self.currentMass
        else:
            # Compute a lower bound on the required mass.
            # For each stage, compute the best possible mass assuming a
            # weightless engine of the best type for the altitude at that
            # stage.  Taking account of altitude makes a huge difference for
            # lower stages, not much for upper stages.
            #
            # Also take account of decoupler mass (and other such per-stage
            # overhead).  This makes a modest difference to all stages,
            # particularly for smaller spacecraft.  Minor nuisance: we don't
            # know how much to charge for the top stage, but there are O(1) top
            # stages, so it doesn't matter much.
            #
            # Improving this heuristic can drastically improve the search time.
            bestMass = self.currentMass
            decouplers = stages.head.decouplerMass if stages else 0
            for i in xrange(len(stages), len(profile.deltaV)):
                (bestProp, bestTank) = burnMass(profile.deltaV[i],
                        profile.maxIsp[i], bestMass)
                bestMass += bestProp
                bestMass += bestTank
                bestMass += decouplers
            self.bestMass = bestMass

    def __lt__(self, other):
        if other is None: return True
        elif isinstance(other, Number): return self.bestMass < other
        else: return self.bestMass < other.bestMass

    def extend(self):
        """
        Return a set of options to add the next stage down on this
        rocket.  The options are sorted by mass.
        """
        assert not self.complete
        # i is the next burn to do
        i = len(self.stages)
        assert i < len(self.profile.deltaV)
        optionsAsparagus = designStage(self.symmetry,
            self.profile.deltaV[i],
            self.currentMass,
            self.profile.altitude[i],
            burnRequirement = self.profile.burnRequirements[i],
            laterStages = self.stages)
        optionsStraight = designStage(self.symmetry,
            self.profile.deltaV[i],
            self.currentMass,
            self.profile.altitude[i],
            burnRequirement = self.profile.burnRequirements[i],
            laterStages = LinkedList.nil)
        options = optionsAsparagus
        options.extend(optionsStraight)
        list.sort(options, key = lambda x: x.fullMass)
        solutions = []
        for stage in options:
            nextstages = LinkedList.cons(stage, self.stages)
            partial = partialSolution(self.profile, nextstages, self.symmetry)
            solutions.append(partial)
        return solutions

    def __str__(self):
        return "\n".join( "\t" + str(s) for s in self.stages )


def designRocket(payload, burnProfiles, massToBeat = None):
    # Initialize the heap of partial solutions.
    partials = [
        partialSolution(burnProfile, LinkedList.nil, symmetry, payload)
            for symmetry in (2, 3) for burnProfile in burnProfiles
    ]
    heapq.heapify(partials)

    # Until the heap is empty, pop off the cheapest partial solution
    # (including the heuristic) and complete it greedily.  In so doing,
    # prune out partial solutions that are too expensive, and stop
    # completing if we get too expensive.
    # Note: there's no pruning until there is a known solution.
    nconsidered = 0
    improved = True
    lastFlushedAt = 0 # Flush if we improve after a long time.
    bestKnown = massToBeat # Note: always compare < bestKnown.
    while len(partials) > 0:
        nconsidered += 1
        if nconsidered % 500 == 0:
            print ("Considered %d candidates so far, %d remaining" %
                    (nconsidered, len(partials)))
            if not improved: pass
            elif not bestKnown: print ("No solution yet...")
            else:
                print ("Best so far:\n%s" % bestKnown)
                improved = False

        candidate = heapq.heappop(partials)
        otherBranches = []
        while candidate < bestKnown and not candidate.complete:
            nextStage = candidate.extend()
            if not nextStage: break
            candidate = nextStage[0]
            otherBranches.extend(nextStage[1:])
        if candidate.complete and candidate < bestKnown:
            bestKnown = candidate
            improved = True
            if lastFlushedAt < nconsidered / 2:
                partials = filter(lambda x: x < bestKnown, partials)
                lastFlushedAt = nconsidered
                heapq.heapify(partials)

        otherBranches = filter(lambda x: x < bestKnown, otherBranches)
        otherBranches.sort()
        for x in otherBranches:
            heapq.heappush(partials, x)

    if bestKnown:
        return bestKnown.stages
    else:
        return None

# In 200s or less, we go from the surface to having apoapsis at 100km,
# using n stages.  Then we circularize at 100km.
# Then, we have a trip to Jool, 1915m/s.
# Then we'll scoot around the Jool system, so let's have another 1km/s.
# Payload is 0.3 tons: a full set of science equipment and an RTG.
# payload = 0.3

# Best known so far:
#    mass 53.265 T, 2 x 1 Aerospike and 6 T fuel, 35.37s burn at 1060 kN (19.90 m/s^2), asparagus
#    mass 36.165 T, 2 x 2 24-77 and 4 T fuel, 35.94s burn at 710 kN (19.63 m/s^2), asparagus
#    mass 26.205 T, 2 x 1 none and 3 T fuel, 28.79s burn at 630 kN (24.04 m/s^2), asparagus
#    mass 18.855 T, 2 x 1 LV-T30 and 2 T fuel, 21.13s burn at 630 kN (33.41 m/s^2), asparagus
#    mass 11.255 T, 1 x 1 LV-T45 and 4 T fuel, 67.38s burn at 200 kN (17.77 m/s^2)
#    mass 4.955 T, 1 x 1 LV-909 and 2 T fuel, 146.90s burn at 50 kN (10.09 m/s^2)
#    mass 1.905 T, 1 x 2 24-77 and 1 T fuel, 26.95s burn at 40 kN (21.00 m/s^2)
#

# Same thing but get Kerbals to Leythe.  But not back -- this is a one-way
# trip.  The lander is 20 tons: a capsule, some living space, RTG, parachutes.
# I dropped down the choices for number of stages to orbit to get this to
# terminate.

# One-way trip to Jool with a lander:
payload = 20
startAltitude = 0
massToBeat = 310.35
# Note: the following isn't necessarily optimal, I stopped when I hit swap.
#        mass 310.35 T, 2 x 3 LV-T30 and 25 T fuel, 24.75s burn at 6120 kN (19.72 m/s^2), asparagus
#        mass 245.7 T, 2 x 2 LV-T30 and 18 T fuel, 25.08s burn at 4830 kN (19.66 m/s^2), asparagus
#        mass 199.4 T, 2 x 2 Mark 55 and 14 T fuel, 24.82s burn at 3970 kN (19.91 m/s^2), asparagus
#        mass 163.7 T, 2 x 2 LV-T30 and 11 T fuel, 23.25s burn at 3490 kN (21.32 m/s^2), asparagus
#        mass 133.15 T, 2 x 1 LV-T30 and 9 T fuel, 25.02s burn at 2630 kN (19.75 m/s^2), asparagus
#        mass 109.8 T, 2 x 3 LV-T45 and 7 T fuel, 24.85s burn at 2200 kN (20.04 m/s^2), asparagus
#        mass 84.15 T, 2 x 2 Aerospike and 12 T fuel, 107.00s burn at 1000 kN (11.88 m/s^2), asparagus
#        mass 50.35 T, 2 x 2 LV-N and 6 T fuel, 277.26s burn at 300 kN (5.96 m/s^2), asparagus
#        mass 27.05 T, 1 x 1 LV-N and 4 T fuel, 409.72s burn at 60 kN (2.22 m/s^2)
#

# One-way trip to Jool with a lander, but with a jet boost to 10km
#    mass 181.94 T, 2 x 13 24-77 and 12 T fuel, 19.92s burn at 3580 kN (19.68 m/s^2), asparagus
#    mass 152 T, 2 x 1 LV-T30 and 9 T fuel, 19.60s burn at 3060 kN (20.13 m/s^2), asparagus
#    mass 128.65 T, 2 x 1 LV-T30 and 7 T fuel, 19.43s burn at 2630 kN (20.44 m/s^2), asparagus
#    mass 109.8 T, 2 x 3 LV-T45 and 6 T fuel, 19.76s burn at 2200 kN (20.04 m/s^2), asparagus
#    mass 86.4 T, 2 x 2 Aerospike and 13 T fuel, 107.70s burn at 1000 kN (11.57 m/s^2), asparagus
#    mass 50.35 T, 2 x 2 LV-N and 6 T fuel, 277.26s burn at 300 kN (5.96 m/s^2), asparagus
#    mass 27.05 T, 1 x 1 LV-N and 4 T fuel, 409.72s burn at 60 kN (2.22 m/s^2)




# Best 10-ton payload to orbit:
#
#    mass 87.625 T, 2 x 1 LV-T30 and 10 T fuel, 35.69s burn at 1730 kN (19.74 m/s^2), asparagus
#    mass 62.025 T, 2 x 1 LV-T30 and 7 T fuel, 33.41s burn at 1300 kN (20.96 m/s^2), asparagus
#    mass 43.175 T, 2 x 1 Mark 55 and 5 T fuel, 34.36s burn at 870 kN (20.15 m/s^2), asparagus
#    mass 29.525 T, 2 x 1 LV-T30 and 3 T fuel, 33.43s burn at 630 kN (21.34 m/s^2), asparagus
#    mass 19.675 T, 1 x 1 LV-T45 and 7 T fuel, 117.72s burn at 200 kN (10.17 m/s^2)





profiles = []
startDeltaV = kerbin.optimalDeltaV(startAltitude)
atmosphericDeltaV = 3200 - startDeltaV

for n in range(1,10):
    print ("designing with %d climb stages" % n)
    # Climb out of the atmosphere.  Acceleration should be at least 2g to
    # maintain the optimal climb profile.
    deltaV = [ atmosphericDeltaV/n for _ in range(n) ]
    burnTimes = [ burnRequirement(acceleration = 2*g0) for _ in range(n) ]

    # Finish climbing and circularize in at most two minutes of burn.
    deltaV.append(1500)
    burnTimes.append( burnRequirement(burnTime = 120) )

    # To Jool!  Burn for up to 5 minutes.
    deltaV.append(1915)
    burnTimes.append( burnRequirement(burnTime = 5*60) )

    # Around Jool.  1 km/s but we don't need much acceleration.
    deltaV.append(1000)
    burnTimes.append( burnRequirement(acceleration = 1) )

    # Design!  Store it in the list of solutions.
    profiles.append(burnProfile(len(deltaV), deltaV, burnTimes))

# Design the rocket!

soln = designRocket(payload, profiles, massToBeat = massToBeat)
if soln:
    print ("Best solution:")
    for x in soln:
        print ("\t%s" % x)
else:
    print "You will not be going to space today."
