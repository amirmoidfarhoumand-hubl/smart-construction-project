import random

class RCPSP_GA:
    def __init__(self, tasks, resources_limit, pop_size=50, generations=100):
        self.tasks = tasks 
        self.res_limits = resources_limit 
        self.pop_size = pop_size
        self.generations = generations

    def generate_chromosome(self):
        chrom = list(self.tasks.keys())
        random.shuffle(chrom)
        return chrom

    def decode_and_evaluate(self, chromosome):
        start_times = {task: 0 for task in chromosome}
        finish_times = {task: 0 for task in chromosome}
        completed = set()
        
        current_time = 0
        while len(completed) < len(chromosome):
            avail_cranes = self.res_limits['Cranes']
            avail_crews = self.res_limits['Crews']
            avail_forms = self.res_limits['Formworks']
            
            for task in chromosome:
                if task not in completed:
                    preds_done = all(p in completed for p in self.tasks[task]['preds'])
                    if preds_done:
                        if (self.tasks[task]['crane'] <= avail_cranes and 
                            self.tasks[task]['crew'] <= avail_crews and 
                            self.tasks[task]['form'] <= avail_forms):
                            
                            start_times[task] = current_time
                            finish_times[task] = current_time + self.tasks[task]['duration']
                            completed.add(task)
                            
                            avail_cranes -= self.tasks[task]['crane']
                            avail_crews -= self.tasks[task]['crew']
                            avail_forms -= self.tasks[task]['form']
            current_time += 1 
            
        makespan = max(finish_times.values())
        return 1.0 / (makespan + 1), makespan, start_times, finish_times

    def crossover(self, p1, p2):
        size = len(p1)
        start, end = sorted(random.sample(range(size), 2))
        child = [None] * size
        child[start:end] = p1[start:end]
        p2_idx = 0
        for i in range(size):
            if child[i] is None:
                while p2[p2_idx] in child:
                    p2_idx += 1
                child[i] = p2[p2_idx]
        return child

    def run(self):
        population = [self.generate_chromosome() for _ in range(self.pop_size)]
        best_makespan = float('inf')
        best_schedule = {}
        makespan_history = [] # ردیابی تاریخچه برای رسم نمودار

        for _ in range(self.generations):
            evaluated = [(chrom, self.decode_and_evaluate(chrom)) for chrom in population]
            evaluated.sort(key=lambda x: x[1][0], reverse=True)
            
            # ذخیره بهترین Makespan در این نسل
            gen_best_makespan = evaluated[0][1][1]
            makespan_history.append(gen_best_makespan)

            if gen_best_makespan < best_makespan:
                best_makespan = gen_best_makespan
                best_schedule = evaluated[0][1]
                
            next_gen = [evaluated[0][0], evaluated[1][0]] 
            
            while len(next_gen) < self.pop_size:
                p1, p2 = random.sample([x[0] for x in evaluated[:15]], 2)
                child = self.crossover(p1, p2)
                if random.random() < 0.2:
                    idx1, idx2 = random.sample(range(len(child)), 2)
                    child[idx1], child[idx2] = child[idx2], child[idx1]
                next_gen.append(child)
                
            population = next_gen
            
        # بازگرداندن تاریخچه در کنار خروجی‌های قبلی
        return best_makespan, best_schedule, makespan_history