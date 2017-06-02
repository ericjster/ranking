import numpy as np
from .BaseRank import BaseRank


class LeastViolatedRank(BaseRank):
    """
    A ranking method which does not utilize the concept of state.
    Equivalent to linear ordering problem, which can be solved by ILP.
    Perhaps very time consuming when number of ranked objects is large. Take care!!
    """
    def __init__(self, minimize=True, verbose=0, solvertp='SCIP', *args, **kwargs):
        """Two options for solvertp:
        'SCIP': ILP backended by http://scip.zib.de/
        'CBC': ILP backedded by https://projects.coin-or.org/Cbc
        """
        super(LeastViolatedRank, self).__init__(*args, **kwargs)
        if solvertp!='SCIP' and solvertp!='CBC':
            raise KeyError("Invalid solver option.")
        self.solvertp = solvertp
        self.minimize = minimize
        self.verbose = verbose

    def rate(self, C):
        """
        C: a potential matrix generated by rankit.util.ConsistancyMatrix
        """
        minimize = self.minimize
        verbose = self.verbose
        solvertp = self.solvertp
        from ortools.linear_solver import pywraplp
        if solvertp=='SCIP':
            solver = pywraplp.Solver('BILP',pywraplp.Solver.SCIP_MIXED_INTEGER_PROGRAMMING)
        else:
            solver = pywraplp.Solver('BILP',pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)

        X=[]
        for i in xrange(C.shape[0]):
            temp = []
            for j in xrange(C.shape[1]):
                temp.append(solver.IntVar(0, solver.infinity(), "x_"+str(i)+"_"+str(j)))
            X.append(temp)


        constraint1=[]
        for i in xrange(C.shape[0]):
            for j in xrange(i, C.shape[1]):
                if i==j: continue;
                constraint1.append(solver.Constraint(1, 1))
                constraint1[-1].SetCoefficient(X[i][j],1)
                constraint1[-1].SetCoefficient(X[j][i],1)

        objective = solver.Objective()
        for i in xrange(C.shape[0]):
            for j in xrange(C.shape[0]):
                if i!=j:
                    objective.SetCoefficient(X[i][j], float(C[i,j]))

        if minimize:
            objective.SetMinimization()
        else:
            objective.SetMaximization()
        status = solver.Solve()
        if status!=0:
            raise RuntimeError("IP solver failed with error code %s"%str(status))
        x=np.fromfunction(np.vectorize(lambda i,j: X[int(i)][int(j)].solution_value()), C.shape, dtype=np.int32)

        niter = 1;
        while True:
            constraint2 = []
            nz = np.vstack(np.nonzero(x))
            for idx in xrange(nz.shape[1]):
                i = nz[0][idx]
                j = nz[1][idx]
                knz = np.nonzero(np.multiply(x[j,:], x[:,i]))[0]
                for k in knz:
                    # add triangle constraint!
                    if i==j or j==k or k==i: continue;
                    constraint2.append(solver.Constraint(-solver.infinity(), 2))
                    constraint2[-1].SetCoefficient(X[i][j], 1)
                    constraint2[-1].SetCoefficient(X[j][k], 1)
                    constraint2[-1].SetCoefficient(X[k][i], 1)
            if len(constraint2)==0:
                if verbose!=0:
                    print("Iteration #%s: %s new triangle constraints added. Problem solved!"\
                    %(str(niter), str(len(constraint2))))
                break;
            else:
                if verbose!=0:
                    print("Iteration #%s: %s new triangle constraints added."\
                    %(str(niter), str(len(constraint2))))
            status = solver.Solve()
            if status!=0:
                raise RuntimeError("IP solver failed with error code %s"%str(status))
            x=np.fromfunction(np.vectorize(lambda i,j: X[int(i)][int(j)].solution_value()), C.shape, dtype=np.int32)
            niter+=1
        return np.sum(x, axis=0)
