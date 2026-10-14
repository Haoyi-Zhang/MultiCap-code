"""Residual classes preserve finite list/dict outputs and canonical ordering."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.residual import all_boolean_tables, execute, synthesize
from src.residual_check import check_residual


class ResidualOutputValuesTests(unittest.TestCase):
    def check_table(self,table,classes):
        before=copy.deepcopy(table)
        for fast in range(4):
            packet=json.loads(json.dumps(synthesize(table,fast)))
            self.assertEqual(packet['class_of_x'],classes)
            self.assertEqual(check_residual(packet)['executions_checked'],len(table)*len(table[0]))
            for x,row in enumerate(table):
                for y,value in enumerate(row):
                    self.assertEqual(execute(packet,x,y),value)
        self.assertEqual(table,before)

    def test_nested_list_and_dictionary_outputs(self):
        a=[{'item':'a','count':2}]
        b=[{'count':2,'item':'a'}]
        c=[{'item':'a','count':1}]
        self.check_table([[a,{'bag':[1,2]}],[b,{'bag':[1,2]}],[c,{'bag':[1,2]}]], [0,0,1])

    def test_structurally_distinct_outputs_remain_distinct(self):
        self.check_table([[None,[]],[None,{}],[None,[]]], [0,1,0])

    def test_boolean_table_class_and_code_order_unchanged(self):
        for table in all_boolean_tables(3,2):
            unique=[]
            classes=[]
            for row in table:
                if row not in unique:
                    unique.append(row)
                classes.append(unique.index(row))
            self.check_table(table,classes)

    def test_equivalent_relabelled_packet_is_not_canonical(self):
        packet=synthesize([[0],[1]],0)
        packet['class_of_x']=[1,0]
        packet['representatives']=[[1],[0]]
        with self.assertRaises(ValueError):
            check_residual(packet)

if __name__=='__main__':
    unittest.main()
